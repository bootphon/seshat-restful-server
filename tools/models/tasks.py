from datetime import datetime
from pathlib import Path
from typing import List

from flask import url_for
from mongoengine import (EmbeddedDocument, ReferenceField, DateTimeField,
                         StringField, Document, BooleanField,
                         EmbeddedDocumentListField, DateField,
                         PULL, ListField, DictField, OperationError)

from tools.models.commons import notif_dispatch
from tools.textgrid_checking.common import TextGridError


class TaskComment(EmbeddedDocument):
    author = ReferenceField('User', required=True)
    creation = DateTimeField(default=datetime.now, required=True)
    text = StringField(required=True)


class FileDownload(EmbeddedDocument):
    downloader = ReferenceField('Annotator', required=True)
    file = StringField(required=True)
    time = DateTimeField(default=datetime.now, equired=True)


class FileUpload(EmbeddedDocument):
    uploader = ReferenceField('Annotator', required=True)
    tg_file = StringField(required=True)
    is_valid = BooleanField(required=True)
    errors = ListField(DictField())
    time = DateTimeField(default=datetime.now, equired=True)

    @classmethod
    def create(cls,
               uploader: 'Annotator',
               textgrid: str,
               errors: List[TextGridError],
               is_valid: bool):
        return cls(uploader=uploader,
                   tg_file=textgrid,
                   is_valid=is_valid,
                   errors=[error.to_dict() for error in errors])


class BaseTask(Document):
    TASK_TYPE = "Tâche de Base"
    meta = {'allow_inheritance': True}
    campaign = ReferenceField('Campaign', required=True)
    assigner = ReferenceField('Admin', required=True)
    creation_time = DateTimeField(default=datetime.now)
    last_update = DateTimeField(default=datetime.now)
    is_done = BooleanField(default=False)
    data_file = StringField(required=True)
    discussion = EmbeddedDocumentListField(TaskComment)
    flagged = BooleanField(default=False)
    deadline = DateField()
    file_downloads = EmbeddedDocumentListField(FileDownload)
    file_uploads = EmbeddedDocumentListField(FileUpload)
    is_locked = BooleanField(default=False)

    @property
    def status(self):
        return "En cours" if not self.is_done else "Terminée"

    @property
    def annotators(self):
        raise NotImplemented()

    @property
    def name(self):
        return self.data_file \
            .strip(Path(self.data_file).suffix) \
            .replace("/", "_")

    @property
    def textgrids(self) -> dict:
        raise NotImplemented()

    @property
    def current_instructions(self):
        raise NotImplemented()

    @property
    def has_started(self):
        raise NotImplemented()

    @property
    def current_tg_template(self):
        raise NotImplemented()

    def get_starter_zip(self) -> bytes:
        raise NotImplemented()

    def _log_upload(self, textgrid, annotator, errors, is_valid: bool = None):
        if is_valid is None:
            is_valid = bool(errors)
        self.file_uploads.append(
            FileUpload.create(annotator, textgrid, [], is_valid)
        )
        self.save()

    def submit_textgrid(self, textgrid: str, annotator: 'Annotator'):
        """Check textgrid, and if passes the validation tests, save it"""
        pass

    def validate_textgrid(self, textgrid: str, annotator: 'Annotator'):
        """Just check the textgrid, raises errors if it's not fully valid.
         Doesn't save the validated textgrid."""
        pass

    def add_comment(self, comment_text: str, author: 'User'):
        if not comment_text.strip():
            return

        new_comment = TaskComment(author=author.id, text=comment_text)
        self.discussion.append(new_comment)
        self.save()

    def save(self, *args, **kwargs):
        self.last_update = datetime.now()
        try:
            super().save(*args, **kwargs)
        except OperationError:
            # This is an ugly and dirty fix: the document tends to overflow the memory limit because of
            # much too large textgrids. The fix is to empty the upload log and then retry saving.
            # I truly hope no god from either the old nor the new will judge me for this
            self.file_uploads.delete()
            super().save(*args, **kwargs)

    @staticmethod
    def notify_assign(annotators: List['Annotator'], campaign: 'Campaign'):
        notif_dispatch(
            message="Vous avez reçu des nouvelles tâches "
                    "à faire sur la campagne %s" % campaign.name,
            notif_type="assignment",
            url=url_for("annotator_dashboard"),
            users=annotators)

    def notify_comment(self, commenter: 'User'):
        from .users import User
        notified_users: List[
            User] = self.annotators + self.campaign.subscribers
        notified_users.remove(commenter)
        notif_dispatch(
            message="Un commentaire a été posté par %s "
                    "sur une tâche sur le fichier %s" % (commenter.full_name,
                                                         self.data_file),
            notif_type="comment",
            url=url_for("task_view", task_id=self.id),
            users=notified_users)

    def notify_flagged(self, flagger: 'Annotator'):
        notif_dispatch(
            message="L'annotateur %s vous averti d'un problème "
                    "sur la tâche du fichier %s" % (
                    flagger.full_name, self.data_file),
            notif_type="alert",
            url=url_for("admin_task_view", task_id=self.id),
            users=self.campaign.subscribers)

    def notify_done(self):
        notif_dispatch(
            message="La tâche sur le fichier %s est terminée " %
                    self.data_file,
            notif_type="finished",
            url=url_for("admin_task_view", task_id=self.id),
            users=self.campaign.subscribers)


from .users import Annotator

BaseTask.register_delete_rule(Annotator, 'assigned_tasks', PULL)
