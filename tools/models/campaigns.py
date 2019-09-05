import zipfile
from collections import Counter
from io import BytesIO

from mongoengine import (Document, StringField, ReferenceField, ListField,
                         PULL, DateTimeField, DoesNotExist)
from datetime import datetime
from pathlib import Path
from os.path import join
from flask import current_app as app

from tools.models.tasks import BaseTask
from tools.utils import percentage
from .commons import DBError
from slugify import slugify


# TODO: set up delete rules (after declaring all classes)


class Campaign(Document):
    name = StringField(max_length=100, required=True)
    slug = StringField(required=True, primary_key=True)
    description = StringField()
    creator = ReferenceField('Admin', required=True)
    subscribers = ListField(ReferenceField('Admin'))
    annotators = ListField(ReferenceField('Annotator'))
    creation_time = DateTimeField(default=datetime.now)
    last_update = DateTimeField(default=datetime.now)
    tasks = ListField(ReferenceField('BaseTask'))
    files_folder_path = StringField(required=True)

    stats = None

    @classmethod
    def create(cls,
               campaign_name: str,
               description: str,
               folder: str,
               creator: 'Admin'):
        campaign_slug = slugify(campaign_name)
        try:
            _ = Campaign.objects.get(slug=campaign_slug)
            raise DBError("Un projet a un nom trop similaire à celui-ci",)
        except DoesNotExist:
            pass

        # TODO : check multiple choice value
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
                for tg_name, tg_str in task.textgrids.items():
                    if tg_str:
                        tg_archpath = task_folder / Path(tg_name + ".TextGrid")
                        zfile.writestr(str(tg_archpath), tg_str)

        return buffer.getvalue()

BaseTask.register_delete_rule(Campaign, 'tasks', PULL)
