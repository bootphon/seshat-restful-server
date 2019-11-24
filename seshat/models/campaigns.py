import zipfile
from datetime import datetime
from io import BytesIO
from pathlib import Path

from mongoengine import (Document, StringField, ReferenceField, ListField,
                         DateTimeField, EmbeddedDocument, EmbeddedDocumentField, BooleanField,
                         ValidationError, signals, PULL, IntField)
from textgrid import TextGrid

from .corpora import CSVCorpus, BaseCorpus
from .tasks import BaseTask
from .textgrids import SingleAnnotatorTextGrid
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
    # either a CSV Corpus or a corpus folder
    corpus: BaseCorpus = ReferenceField('BaseCorpus', required=True)
    # the audio file is being served in the starter zip
    serve_audio = BooleanField(default=False)
    # this object stores the campaign annotation checking scheme
    checking_scheme: TextGridCheckingScheme = ReferenceField(TextGridCheckingScheme)
    # if this is false, textgrid aren't checked (except for the merge part)
    check_textgrids = BooleanField(default=True)
    # updated on trigger
    stats = EmbeddedDocumentField(CampaignStats)

    def validate(self, clean=True):
        if isinstance(self.corpus, CSVCorpus) and self.serve_audio:
            raise ValidationError("Can't serve audio files with a csv corpus")
        super().validate(clean)

    @classmethod
    def post_delete_cleanup(cls, sender, document: 'Campaign', **kwargs):
        """Called upon a post_delete event. Takes care of cleaning up stuff, deleting the campaigns's
        child tasks"""
        for task in document.tasks:
            task.delete()

    def tasks_for_file(self, audio_file: str):
        tasks = [task for task in self.tasks]
        return len([task for task in tasks if task.data_file == audio_file])

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

    def gen_template_tg(self, filename: str) -> SingleAnnotatorTextGrid:
        audio_file = self.corpus.files[filename]
        if self.checking_scheme is None:
            tg = TextGrid(name=filename, maxTime=audio_file.duration)
        else:
            tg = self.checking_scheme.gen_template_tg(audio_file.duration, filename)
        return SingleAnnotatorTextGrid.from_textgrid(tg, [self.creator], None)

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
            "description": self.description,
            "creator": self.creator.short_profile,
            # TODO use the stats object when it's completed and rightly updated
            "stats": {
                "total_tasks": len(self.tasks),
                "completed_tasks": len([task for task in self.tasks if task.is_done]),
                "total_files": self.corpus.files_count,
                "assigned_files": len(set(task.data_file for task in self.tasks)),
            },
            "corpus_path": self.corpus.name,
            "tiers_number": len(self.checking_scheme.tiers_specs) if self.checking_scheme is not None else None,
            "check_textgrids": self.check_textgrids,
            "annotators": [annotator.short_profile for annotator in self.annotators],
            "subscribers": [user.username for user in self.subscribers]
        }

signals.post_delete.connect(Campaign.post_delete_cleanup, sender=Campaign)
BaseTask.register_delete_rule(Campaign, 'tasks', PULL)