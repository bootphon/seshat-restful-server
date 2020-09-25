import zipfile
from datetime import datetime
from enum import Enum
from io import BytesIO
from pathlib import Path
from typing import Dict, Optional, List

from flask import current_app
from mongoengine import EmbeddedDocument, ReferenceField, DateTimeField, StringField, BooleanField, Document, \
    EmbeddedDocumentListField, DateField, Q, ValidationError
from mongoengine import (PULL, NULLIFY, signals)

from ..commons import notif_dispatch
from ..textgrids import BaseTextGridDocument
from ..textgrids import LoggedTextGrid


class TaskComment(EmbeddedDocument):
    author = ReferenceField('User', required=True)
    creation = DateTimeField(default=datetime.now, required=True)
    text = StringField(required=True)

    @property
    def to_msg(self):
        return {"author": self.author.short_profile,
                "creation": self.creation,
                "content": self.text}


class FileDownload(EmbeddedDocument):
    downloader = ReferenceField('Annotator', required=True)
    file = StringField(required=True)
    time = DateTimeField(default=datetime.now, equired=True)


class FileUpload(EmbeddedDocument):
    tg_file = ReferenceField('LoggedTextGrid', required=True)
    is_valid = BooleanField(required=True)


class BaseTask(Document):
    TASK_TYPE = "Base Task"
    meta = {'allow_inheritance': True}
    campaign = ReferenceField('Campaign', required=True)
    assigner = ReferenceField('Admin', required=True)
    creation_time = DateTimeField(default=datetime.now)
    last_update = DateTimeField(default=datetime.now)
    finish_time = DateTimeField()
    is_done = BooleanField(default=False)
    is_locked = BooleanField(default=False)
    data_file = StringField(required=True)
    discussion = EmbeddedDocumentListField(TaskComment)
    deadline = DateField()
    file_downloads: List[FileDownload] = EmbeddedDocumentListField(FileDownload)
    file_uploads: List[FileUpload] = EmbeddedDocumentListField(FileUpload)

    # Only contains one Tier ("Task")  of the audio file's length
    # with nothing in it.
    template_tg = ReferenceField(BaseTextGridDocument)
    # the final annotated file, with 4 tiers
    final_tg = ReferenceField(BaseTextGridDocument)

    class Steps(Enum):
        PENDING = 1
        DONE = 2

    steps_names = {
        Steps.PENDING: "Pending",
        Steps.DONE: "Done"
    }

    # TODO : make the instruction different depending on if the audio file is in the archive or not.
    INITIAL_TEMPLATE_INSTRUCTIONS = """Annotate the audio file using the downloadable template 
    textgrid in the archive."""

    @property
    def current_step(self) -> Steps:
        if not self.has_started:
            return self.Steps.PENDING
        else:
            return self.Steps.DONE

    @classmethod
    def post_delete_cleanup(cls, sender, document: 'BaseTask', **kwargs):
        """Removing notifications affiliated to that task"""
        from ..users import Notification
        Notification.objects(Q(object_id=str(document.id)) & Q(object_type="task")).delete()
        document.campaign.update_stats()

    @classmethod
    def pre_save(cls, sender, document: 'BaseTask', **kwargs):
        #  TODO set up post save that also updates the campaign's last_update
        document.last_update = datetime.now()

    @property
    def annotators(self):
        raise NotImplemented()

    @property
    def has_started(self):
        return len(self.file_downloads) > 0 or len(self.file_uploads) > 0

    @property
    def start_time(self) -> Optional[datetime]:
        """Time of the first file download of a tasks's file, ergo, the
        estimated start time of the task"""
        return self.file_downloads[0].time if self.file_downloads else None

    @property
    def name(self):
        return self.data_file \
            .strip(Path(self.data_file).suffix) \
            .replace("/", "_")

    @property
    def textgrids(self) -> Dict[str, Optional[BaseTextGridDocument]]:
        raise NotImplemented()

    def delete_textgrid(self, tg_name: str):
        """Just 'forgetting' textgrid for this task, not actually removing the textgrid from the database"""
        # TODO : add a "reset to step x" functionnality
        self.__setattr__(tg_name + "_tg", None)
        self.is_done = False
        self.save()
        self.campaign.update_stats()

    @property
    def allow_starter_zip_dl(self) -> bool:
        raise NotImplemented()

    def allow_file_upload(self, annotator: 'Annotator') -> bool:
        raise NotImplemented()

    def current_instructions(self, user: 'Annotator') -> str:
        raise NotImplemented()

    def current_tg_template(self, user: 'Annotator') -> str:
        raise NotImplemented()

    def get_starter_zip(self) -> bytes:
        """Generates a zip file containing the template tg, and optionally
        the audio file that is to be annotated"""
        buffer = BytesIO()
        with zipfile.ZipFile(buffer, "w", zipfile.ZIP_STORED) as zfile:
            zip_folder: str = self.name
            if self.campaign.serve_audio:
                audio_filepath = (Path(current_app.config["CAMPAIGNS_FILES_ROOT"]) / Path(self.data_file))
                audio_arcname = Path(zip_folder) / Path(Path(self.data_file).name)
                zfile.write(str(audio_filepath), audio_arcname)

            textgrid_archname = (Path(zip_folder) /
                                 Path(Path(self.data_file).stem + ".TextGrid"))
            zfile.writestr(str(textgrid_archname), self.template_tg.to_str())

        return buffer.getvalue()

    def _log_upload(self, textgrid: str,
                    annotator: 'Annotator',
                    is_valid: bool = None):
        logged_tg = LoggedTextGrid.from_textgrid(textgrid, [annotator], self)
        logged_tg.save()
        self.file_uploads.append(
            FileUpload(tg_file=logged_tg, is_valid=is_valid)
        )
        self.save()

    def log_download(self, downloader: 'Annotator', file_name: str):
        self.file_downloads.append(
            FileDownload(downloader=downloader, file=file_name)
        )
        self.save()

    @property
    def short_status(self):
        return {
            "id": self.id,
            "filename": self.data_file,
            "campaign": self.campaign.short_profile,
            "deadline": self.deadline,
            "task_type": self.TASK_TYPE,
            "annotators": [user.id for user in self.annotators],
            "assigner": self.assigner.short_profile,
            "creation_time": self.creation_time,
            "step": self.steps_names[self.current_step],
            "is_locked": self.is_locked,
            "is_done": self.is_done,
            "finish_time": self.finish_time
        }

    @property
    def admin_status(self):
        textgrids = []
        for tg_name, tg in self.textgrids.items():
            tg_dict = {"name": tg_name,
                       "has_been_submitted": bool(tg)}
            if tg is not None:
                tg_dict.update(tg.task_tg_msg)
            textgrids.append(tg_dict)

        return {**self.short_status,
                "campaign": self.campaign.short_profile,
                "textgrids": textgrids}

    def get_annotator_status(self, annotator: 'Annotator'):
        return {
            **self.short_status,
            "all_steps": [self.steps_names[step] for step in self.Steps],
            "current_step_idx": self.current_step.value,
            "current_instructions": self.current_instructions(annotator),
            "allow_starter_dl": self.allow_starter_zip_dl,
            "allow_file_upload": self.allow_file_upload(annotator),
        }

    def submit_textgrid(self, textgrid: str, annotator: 'Annotator'):
        """Check textgrid, and if passes the validation tests, save it"""
        pass

    def validate_textgrid(self, textgrid: str, annotator: 'Annotator'):
        """Just check the textgrid, raises errors if it's not fully valid.
         Doesn't save the validated textgrid."""
        pass

    def add_comment(self, comment_text: str, author: 'User'):
        if not comment_text.strip():
            ValidationError("Can't submit empty comment.")

        new_comment = TaskComment(author=author.id, text=comment_text)
        self.discussion.append(new_comment)
        self.save()

    @staticmethod
    def notify_assign(annotators: List['Annotator'], campaign: 'Campaign'):
        notif_dispatch(
            message="You were assigned new tasks on campaign %s" % campaign.name,
            notif_type="assignment",
            object_type="dashboard",
            object_id=campaign.slug,
            users=annotators)

    def notify_comment(self, commenter: 'User'):
        from ..users import User
        notified_users: List[User] = self.annotators + self.campaign.subscribers
        notified_users.remove(commenter)
        notif_dispatch(
            message="%s commented on the annotation task on file %s"
                    % (commenter.full_name, self.data_file),
            notif_type="comment",
            object_type="task",
            object_id=str(self.id),
            users=notified_users)

    def notify_done(self):
        notif_dispatch(
            message="The annotation task on file %s is done" % self.data_file,
            notif_type="finished",
            object_type="task",
            object_id=str(self.id),
            users=self.campaign.subscribers)


from ..users import Annotator

# the signals have to registered with child classes as well.
signals.post_delete.connect(BaseTask.post_delete_cleanup, sender=BaseTask)
signals.pre_save.connect(BaseTask.pre_save, sender=BaseTask)
BaseTask.register_delete_rule(Annotator, 'assigned_tasks', PULL)
BaseTask.register_delete_rule(BaseTextGridDocument, 'task', NULLIFY)
