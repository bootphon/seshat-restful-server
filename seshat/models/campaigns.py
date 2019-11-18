import logging
import zipfile
from collections import Counter
from csv import DictReader
from datetime import datetime
from functools import lru_cache
from io import BytesIO
from pathlib import Path
from typing import Dict

import ffmpeg
from flask import current_app
from mongoengine import (Document, StringField, ReferenceField, ListField,
                         DateTimeField, EmbeddedDocument, EmbeddedDocumentField, BooleanField,
                         ValidationError, NULLIFY, signals, PULL, IntField)
from textgrid import TextGrid

from .tasks import BaseTask
from .textgrids import BaseTextGridDocument, SingleAnnotatorTextGrid
from seshat.utils import percentage
from .tg_checking import TextGridCheckingScheme


class CampaignStats(EmbeddedDocument):
    """Stores the campaing basic statistics"""
    # TODO add "refresh campaign stats handler"
    total_files = IntField(required=True)
    assigned_files = IntField(required=True)
    total_tasks = IntField(required=True)
    completed_tasks = IntField(required=True)

    def to_msg(self):
        return {"total_files": self.total_files,
                "assigned_files": self.assigned_files,
                "total_tasks": self.total_tasks,
                "completed_tasks": self.completed_tasks}


class Campaign(Document):
    name = StringField(max_length=100, required=True)
    slug = StringField(required=True, primary_key=True)
    description = StringField()
    creator = ReferenceField('Admin', required=True)
    subscribers = ListField(ReferenceField('Admin'))
    creation_time = DateTimeField(default=datetime.now)
    last_update = DateTimeField(default=datetime.now)
    wiki_page = StringField()
    tasks = ListField(ReferenceField('BaseTask'))
    # either the CSV or the data folder
    corpus_path = StringField(required=True)
    # the audio file is being served in the starter zip
    serve_audio = BooleanField(default=False)
    # this object stores the campaign annotation checking scheme
    checking_scheme: TextGridCheckingScheme = ReferenceField(TextGridCheckingScheme)
    # if this is false, textgrid aren't checked (except for the merge part)
    check_textgrids = BooleanField(default=True)
    # updated on trigger
    stats = EmbeddedDocumentField(CampaignStats)

    def validate(self, clean=True):
        if self.corpus_type == "csv" and self.serve_audio:
            raise ValidationError("Can't serve audio files with a csv corpus")
        super().validate(clean)

    @classmethod
    def post_delete_cleanup(cls, sender, document: 'Campaign', **kwargs):
        """Called upon a post_delete event. Takes care of cleaning up stuff, deleting the campaigns's
        child tasks"""
        for task in document.tasks:
            task.delete()

    @property
    def real_corpus_path(self):
        return Path(current_app.config["CAMPAIGNS_FILES_ROOT"]) / Path(self.corpus_path)

    @property
    def corpus_type(self) -> str:
        corpus_path = self.real_corpus_path
        if corpus_path.is_dir():
            return "folder"
        elif corpus_path.is_file() and corpus_path.suffix == ".csv":
            return "csv"
        else:
            logging.warning("Corpus %s isn't csv file or data folder" % str(corpus_path))

    @property
    @lru_cache(maxsize=1024) # TODO : maybe tweak this caching value?
    def csv_table(self):
        csv_path = self.real_corpus_path
        with open(str(csv_path), "r") as csv_data_file:
            reader = DictReader(csv_data_file)
            return {row["filename"]: float(row["duration"]) for row in reader}

    def get_file_duration(self, filename: str):
        if self.corpus_type == "csv":
            return self.csv_table[filename]
        else:
            filepath = Path(current_app.config["CAMPAIGNS_FILES_ROOT"]) / Path(filename)
            return float(ffmpeg.probe(str(filepath))["format"]["duration"])

    def populate_audio_files(self):
        if self.corpus_type == "csv":
            with open(str(self.real_corpus_path), "r") as csv_data_file:
                reader = DictReader(csv_data_file)
                if not set(reader.fieldnames) == {"filename", "duration"}:
                    raise ValueError("The CSV data file doesn't have the right headers (filename and duration)")
                return [row["filename"] for row in reader]

        else:  # it's an audio file tree
            audio_files = []
            authorized_extensions = current_app.config["SUPPORTED_AUDIO_EXTENSIONS"]
            for filepath in self.real_corpus_path.glob("**/*"):
                if filepath.suffix.strip(".") in authorized_extensions:
                    audio_files.append(str(Path(*filepath.parts[1:])))
            return audio_files

    def _tasks_for_file(self, audio_file: str):
        tasks = [task for task in self.tasks]
        return len([task for task in tasks if task.data_file == audio_file])

    @property
    def files(self):
        return [{"path": file_path,
                 "tasks_count": self._tasks_for_file(file_path),
                 "type": Path(file_path).suffix.strip(".")
                 }
                for file_path in self.populate_audio_files()]

    @property
    def active_tasks(self):
        return BaseTask.objects(campaign=self.id, is_done=False)

    @property
    def annotators(self):
        all_annotators = set()
        for task in self.tasks:
            for annotator in task.annotators:
                all_annotators.add(annotator)
        return list(all_annotators)

    def compute_short_stats(self):
        # TODO update this
        tasks = {
            "done": len([task for task in self.tasks if task.is_done]),
            "assigned": len(self.tasks)
        }
        tasks["percentage"] = percentage(tasks["done"], tasks["assigned"])

        all_audio_files = self.populate_audio_files()
        files = {
            "total": len(all_audio_files),
            "tasked": len(set(task.data_file for task in self.tasks)
                          .intersection(set(map(str, all_audio_files))))
        }
        files["percentage"] = percentage(files["tasked"], files["total"])
        self.stats = {
            "tasks": tasks,
            "files": files,
        }

    def compute_full_stats(self):
        # TODO change this
        self.compute_short_stats()

        all_assignments = []
        for task in self.tasks:
            all_assignments += task.annotators
        all_assignments = map(lambda x: x.username, all_assignments)
        assignments_counts = Counter(all_assignments)
        self.stats["assignments_counts"] = assignments_counts

    def gen_template_tg(self, filename: str) -> SingleAnnotatorTextGrid:
        file_duration = self.get_file_duration(filename)
        if self.checking_scheme is None:
            tg = TextGrid(name=filename, maxTime=file_duration)
        else:
            tg = self.checking_scheme.gen_template_tg(file_duration, filename)
        return SingleAnnotatorTextGrid.from_textgrid_obj(tg, [self.creator], None)

    def get_full_annots_archive(self):
        buffer = BytesIO()
        with zipfile.ZipFile(buffer, "w", zipfile.ZIP_STORED) as zfile:
            zip_folder: Path = Path(self.slug)
            for task in self.tasks:
                task_annotators = "-".join([annotator.username
                                            for annotator in task.annotators])
                task_datafile = task.data_file.strip(
                    Path(task.data_file).suffix)
                task_folder = (zip_folder /
                               Path(task_datafile) /
                               Path(task_annotators))
                for tg_name, tg_doc in task.textgrids.items():
                    if tg_doc is not None:
                        tg_archpath = task_folder / Path(tg_name + ".TextGrid")
                        zfile.writestr(str(tg_archpath), tg_doc.to_str())

        return buffer.getvalue()

    @property
    def short_profile(self):
        return {"slug": self.slug,
                "name": self.name}

    @property
    def status(self):
        return {
            "slug": self.slug,
            "name": self.name,
            "creator": self.creator.short_profile,
            # TODO use the stats object when it's completed and rightly updated
            "stats": {
                "total_tasks": len(self.tasks),
                "completed_tasks": len([task for task in self.tasks if task.is_done]),
                "total_files": len(self.populate_audio_files()),
                "assigned_files": len(set(task.data_file for task in self.tasks)),
            },
            "corpus_path": self.corpus_path,
            "tiers_number": len(self.checking_scheme.tiers_specs) if self.checking_scheme is not None else None,
            "check_textgrids": self.check_textgrids,
            "annotators": [annotator.short_profile for annotator in self.annotators],
            "subscribers": [user.username for user in self.subscribers]
        }

signals.post_delete.connect(Campaign.post_delete_cleanup, sender=Campaign)
BaseTask.register_delete_rule(Campaign, 'tasks', PULL)