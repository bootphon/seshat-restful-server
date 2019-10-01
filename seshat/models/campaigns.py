import zipfile
from collections import Counter
from datetime import datetime
from io import BytesIO
from pathlib import Path

from flask import current_app as app
from mongoengine import (Document, StringField, ReferenceField, ListField,
                         PULL, DateTimeField, DoesNotExist, EmbeddedDocument, EmbeddedDocumentField, BooleanField)
from slugify import slugify

from seshat.models import BaseTask
from seshat.utils import percentage
from .commons import DBError
from .tg_checking import TextGridCheckingScheme


# TODO: set up delete rules (after declaring all classes)

class CampaignStats(EmbeddedDocument):
    """Stores the campaing basic statistics"""
    pass


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
    files_folder_path = StringField(required=True)
    # the audio file is being served in the starter zip
    serve_audio = BooleanField(default=False)
    # this object stores the campaign annotation checking scheme
    checking_scheme = ReferenceField(TextGridCheckingScheme)
    # if this is false, textgrid aren't checked (except for the merge part)
    check_textgrid = BooleanField(default=True)
    # updated on trigger
    stats = EmbeddedDocumentField(CampaignStats)

    @classmethod
    def create(cls,
               campaign_name: str,
               description: str,
               folder: str,
               creator: 'Admin'):
        campaign_slug = slugify(campaign_name)
        try:
            _ = Campaign.objects.get(slug=campaign_slug)
            raise DBError("Un projet a un nom trop similaire à celui-ci", )
        except DoesNotExist:
            pass

        # TODO : refactor this full function to use the schema
        files_folder = Path(app.config["CAMPAIGNS_FILES_ROOT"]) / Path(folder)
        new_campaign = Campaign(name=campaign_name,
                                slug=campaign_slug,
                                description=description,
                                files_folder_path=str(files_folder),
                                creator=creator.id,
                                subscribers=[creator.id])
        new_campaign.save()
        return new_campaign

    def populate_audio_files(self):
        p = Path(self.files_folder_path)
        return [Path(*f.parts[1:]) for f in p.glob("**/*") if f.suffix == ".wav"]

    def _tasks_for_file(self, audio_file: str):
        tasks = [task for task in self.tasks]
        return len([task for task in tasks if task.data_file == audio_file])

    @property
    def files(self):
        return [{"path": str(file_path),
                 "tasks_count": self._tasks_for_file(str(file_path)),
                 "type": file_path.suffix.strip(".")
                 }
                for file_path in self.populate_audio_files()]

    @property
    def active_tasks(self):
        return BaseTask.objects(campaign=self.id, is_done=False)

    def compute_short_stats(self):
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
        self.compute_short_stats()

        all_assignments = []
        for task in self.tasks:
            all_assignments += task.annotators
        all_assignments = map(lambda x: x.username, all_assignments)
        assignments_counts = Counter(all_assignments)
        self.stats["assignments_counts"] = assignments_counts

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
                for tg_name, tg_doc in task.files.items():
                    if tg_doc is not None:
                        tg_archpath = task_folder / Path(tg_name + ".TextGrid")
                        zfile.writestr(str(tg_archpath), tg_doc.to_str())

        return buffer.getvalue()


BaseTask.register_delete_rule(Campaign, 'tasks', PULL)
