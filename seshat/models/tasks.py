import zipfile
from datetime import datetime
from enum import Enum
from io import BytesIO, StringIO
from pathlib import Path
from typing import List, Dict, Optional

import ffmpeg
from flask import current_app
from mongoengine import (EmbeddedDocument, ReferenceField, DateTimeField,
                         StringField, Document, BooleanField,
                         EmbeddedDocumentListField, DateField,
                         FloatField, IntField, EmbeddedDocumentField,
                         PULL, NULLIFY, ValidationError)
from textgrid import TextGrid, IntervalTier

from seshat.models.errors import MergeConflictsError
from seshat.models.textgrids import MergedAnnotsTextGrid
from .commons import notif_dispatch
from .errors import error_log
from .textgrids import MergedTimesTextGrid, BaseTextGridDocument, SingleAnnotatorTextGrid


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
    uploader = ReferenceField('Annotator', required=True)
    tg_file = ReferenceField('BaseTextGridDocument', required=True)
    is_valid = BooleanField(required=True)
    time = DateTimeField(default=datetime.now, equired=True)

    @classmethod
    def create(cls,
               uploader: 'Annotator',
               textgrid: 'BaseTextGridDocument',
               is_valid: bool):
        return cls(uploader=uploader,
                   tg_file=textgrid,
                   is_valid=is_valid)


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
    file_downloads = EmbeddedDocumentListField(FileDownload)
    file_uploads = EmbeddedDocumentListField(FileUpload)

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

    @property
    def annotators(self):
        raise NotImplemented()

    @property
    def has_started(self):
        return len(self.file_downloads) > 0

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

    @property
    def allow_starter_zip_dl(self) -> bool:
        raise NotImplemented()

    @property
    def allow_file_upload(self) -> bool:
        raise NotImplemented()

    def current_instructions(self, user: 'Annotator') -> str:
        raise NotImplemented()

    def current_tg_template(self, user: 'Annotator') -> str:
        raise NotImplemented()

    def create_task_template(self, data_file: str):
        duration = float(ffmpeg.probe(data_file)["format"]["duration"])
        new_tg = TextGrid(name=data_file,
                          minTime=0.0,
                          maxTime=duration)
        for tier_name in self.campaign.checking_scheme.all_tier_names:
            new_tier = IntervalTier(name=tier_name,
                                    minTime=0.0,
                                    maxTime=duration)
            new_tg.append(new_tier)
        self.template_tg = SingleAnnotatorTextGrid.from_textgrid_obj(new_tg, [], self)

    def get_starter_zip(self) -> bytes:
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

    def _log_upload(self, textgrid, annotator, errors, is_valid: bool = None):
        if is_valid is None:
            is_valid = bool(errors)
        self.file_uploads.append(
            FileUpload.create(annotator, textgrid, is_valid)
        )
        self.save()

    def log_download(self, downloader: 'Annotator', file_name: str):
        self.file_downloads.append(
            FileDownload(downloader=downloader.id,
                         file=file_name)
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
            "is_done": self.is_done
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
            "allow_file_upload": self.allow_file_upload,
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

    def save(self, *args, **kwargs):
        # TODO set up post save that also updates the campaign's last_update
        self.last_update = datetime.now()
        super().save(*args, **kwargs)

    @staticmethod
    def notify_assign(annotators: List['Annotator'], campaign: 'Campaign'):
        notif_dispatch(
            message="You were assigned new tasks on campaign %s" % campaign.name,
            notif_type="assignment",
            object_type="dashboard",
            object_id=None,
            users=annotators)

    def notify_comment(self, commenter: 'User'):
        from .users import User
        notified_users: List[User] = self.annotators + self.campaign.subscribers
        notified_users.remove(commenter)
        notif_dispatch(
            message="Annotator %s commented on the annotation task on file %s"
                    % (commenter.full_name, self.data_file),
            notif_type="comment",
            object_type="task",
            object_id=self.id,
            users=notified_users)

    def notify_done(self):
        notif_dispatch(
            message="The annotation task on file %s is done" % self.data_file,
            notif_type="finished",
            object_type="task",
            object_id=self.id,
            users=self.campaign.subscribers)


class SingleAnnotatorTask(BaseTask):
    TASK_TYPE = "Single Annotator"
    annotator = ReferenceField('Annotator', required=True)

    class Steps(Enum):
        PENDING = 0
        IN_PROGRESS = 1
        DONE = 2

    steps_names = {
        Steps.PENDING: "Pending",
        Steps.IN_PROGRESS: "In Progress",
        Steps.DONE: "Done"
    }

    @property
    def current_step(self) -> Steps:
        if not self.has_started:
            return self.Steps.PENDING

        if self.is_done:
            return self.Steps.DONE
        else:
            return self.Steps.IN_PROGRESS

    @property
    def annotators(self):
        return [self.annotator]

    @property
    def allow_file_upload(self) -> bool:
        return True

    @property
    def allow_starter_zip_dl(self):
        return self.current_step in (self.Steps.PENDING, self.Steps.IN_PROGRESS)

    def current_instructions(self, user: 'Annotator') -> str:
        return self.INITIAL_TEMPLATE_INSTRUCTIONS

    def current_tg_template(self, user: 'Annotator') -> str:
        if self.final_tg is None:
            return "tasks_template"
        else:
            return "final"

    @property
    def textgrids(self) -> Dict[str, Optional[BaseTextGridDocument]]:
        return {
            "template": self.template_tg,
            "final": self.final_tg
        }

    def submit_textgrid(self, textgrid: str, annotator: 'Annotator'):
        if self.is_locked:
            return

        tg = SingleAnnotatorTextGrid.from_textgrid_str(textgrid, self.annotators, self)
        tg.check()
        if not error_log.has_errors:
            self.final_tg = tg
            self.is_done = True
            self.finish_time = datetime.now()
            self.notify_done()

        self.cascade_save()
        self._log_upload(textgrid, annotator, not error_log.has_errors)

    def validate_textgrid(self, textgrid: str, annotator: 'Annotator'):
        if self.is_locked:
            return

        error_log.flush()
        tg = SingleAnnotatorTextGrid.from_textgrid_str(textgrid, [self.annotator], self)

        tg.check()
        self._log_upload(textgrid, annotator, not error_log.has_errors)


class FrontierMerge(EmbeddedDocument):
    time_a = FloatField(required=True)
    time_b = FloatField(required=True)
    interval_index_before = IntField(required=True)
    interval_index_after = IntField(required=True)
    could_merge = BooleanField(required=True)
    merged_time = FloatField()


class TierMerge(EmbeddedDocument):
    tier_a = StringField(required=True)
    tier_b = StringField(required=True)
    frontiers_merge = EmbeddedDocumentListField(FrontierMerge)


class MergeResults(EmbeddedDocument):
    tiers_merges = EmbeddedDocumentListField(TierMerge)

    def to_merge_conflicts_errors(self):
        for tier_merge in self.tiers_merges:
            for frontier_merge in tier_merge.frontiers_merge:
                if not frontier_merge.could_merge:
                    yield MergeConflictsError(
                        tier_a=tier_merge.tier_a,
                        tier_b=tier_merge.tier_b,
                        time_a=frontier_merge.time_a,
                        time_b=frontier_merge.time_b,
                        index_before=frontier_merge.interval_index_before)


class DoubleAnnotatorTask(BaseTask):
    TASK_TYPE = "Double Annotators"
    reference = ReferenceField('Annotator', required=True)
    target = ReferenceField('Annotator', required=True)
    # fully annotated textgrid from the ref annotator
    ref_tg = StringField()
    # fully annotated textgrid from the target annotator
    target_tg = StringField()
    # target and ref annotated tg's stacked one onto another, for annotation
    # merging
    merged_tg = StringField()
    times_conflicts = EmbeddedDocumentField(MergeResults)
    # target and ref still stacked, but all annotations are the same
    merged_annots_tg = StringField()
    # times that could be merged automatically are merged, annotators have to
    # agree on frontiers that are too "far away" from each other
    merged_times_tg = StringField()

    class Steps(Enum):
        PENDING = 0
        PARALLEL = 1
        TIERS_AGREEMENT = 2
        MERGING_ANNOTS = 3
        MERGING_TIMES = 4
        DONE = 5

    steps_names = {
        Steps.PENDING: "Pending",
        Steps.PARALLEL: "Parallel Annotations",
        Steps.TIERS_AGREEMENT: "Agreement on tiers",
        Steps.MERGING_ANNOTS: "Merging annotations",
        Steps.MERGING_TIMES: "Merging Times"
    }

    INITIAL_TEMPLATE_INSTRUCTIONS = \
        """Annotate the file using the protocol defined by your annotation manager"""

    WAIT_FOR_OTHER_ANNOTATOR_INSTRUCTIONS = \
        """Wait for the %s annotator to finish her job. Meanwhile, if you think your work is worth 
        improving, you can still upload new versions of your annotated file."""

    CANT_MAKE_MERGED = \
        """Your TextGrid can't be merged for now because some tiers mismatch. Please make sure that the
        tiers in both your annotated file and your partner's are the same."""

    REF_MERGE_ANNOTS_INSTRUCTIONS = \
        """The 'Target' annotator should join you at this point. Your job is to find some 
        agreement on the number of annotations and their content. Your goal is to have, for each pair 
        of matching reference and target tier, the exact same amount of annotations with the same values. 
        You don't have to agree on the timing of those annotations yet."""

    TARGET_MERGE_ANNOTS_INSTRUCTIONS = \
        """Joint the reference annotator now, so you can (together) find an agreement based on 
        your respective annotations. The merged file is to be edited on the reference annotator's 
        computer."""

    REF_MERGE_TIMES_INSTRUCTIONS = \
        """Together with the Target annotator, make sure the Frontiers that still couldn't
         be merged are closer to one another (a difference smaller than %ims). 
         The Frontiers that had too big of a mismatch are listed underneath.""" \
        % int(MergedAnnotsTextGrid.DIFF_THRESHOLD * 1000)

    TARGET_MERGE_TIMES_INSTRUCTIONS = \
        """Still with the Reference annotator, finish merging the Frontier's timing mismatches 
        of the merged file. The merging has to be done on her computer. As a way to help her, 
        the Frontiers that had too big of a mismatch are listed underneath."""

    @property
    def current_step(self) -> Steps:
        if not self.has_started:
            return self.Steps.PENDING

        if self.is_done:
            return self.Steps.DONE

        if self.merged_annots_tg is not None:
            return self.Steps.MERGING_TIMES

        if self.merged_tg is not None:
            return self.Steps.MERGING_ANNOTS

        if self.target_tg is not None and self.ref_tg is not None:
            return self.Steps.TIERS_AGREEMENT

        return self.Steps.PARALLEL

    @property
    def annotators(self):
        return [self.reference, self.target]

    def notify_merged_ready(self, annotator: 'Annotator'):
        notif_dispatch(
            message=("The other annotator has finished their job on the double-annotation task for file %s"
                     % self.data_file),
            notif_type="finished",
            object_type="task",
            object_id=self.id,
            users=[annotator])

    def current_instructions(self, user: 'Annotator') -> str:
        if user == self.reference:
            if self.ref_tg is None:
                return self.INITIAL_TEMPLATE_INSTRUCTIONS

            elif self.ref_tg is not None and self.target_tg is None:
                return self.WAIT_FOR_OTHER_ANNOTATOR_INSTRUCTIONS % "target"

            elif self.ref_tg is not None and self.ref_tg is not None and self.merged_tg is None:
                return self.CANT_MAKE_MERGED

            elif self.merged_annots_tg is None:
                return self.REF_MERGE_ANNOTS_INSTRUCTIONS

            else:
                return self.REF_MERGE_TIMES_INSTRUCTIONS

        else:  # it's the target annotator
            if self.target_tg is None:
                return self.INITIAL_TEMPLATE_INSTRUCTIONS

            elif self.ref_tg is None and self.target_tg is not None:
                return self.WAIT_FOR_OTHER_ANNOTATOR_INSTRUCTIONS % "reference"

            elif self.ref_tg is not None and self.ref_tg is not None and self.merged_tg is None:
                return self.CANT_MAKE_MERGED

            elif self.merged_annots_tg is None:
                return self.TARGET_MERGE_ANNOTS_INSTRUCTIONS

            else:
                return self.TARGET_MERGE_TIMES_INSTRUCTIONS

    @property
    def textgrids(self) -> Dict[str, Optional[BaseTextGridDocument]]:
        return {
            "template": self.template_tg,
            "ref": self.ref_tg,
            "target": self.target_tg,
            "merged": self.merged_tg,
            "merged_annots": self.merged_annots_tg,
            "merged_times": self.merged_times_tg,
            "final": self.final_tg
        }

    def current_tg_template(self, user: 'Annotator') -> str:
        if self.merged_tg is None:
            if user == self.reference:
                if self.ref_tg is None:
                    return "template"
                else:
                    return "ref"
            else:  # it's the target
                if self.target_tg is None:
                    return "template"
                else:
                    return "target"
        elif self.merged_annots_tg is None:
            return "merged"
        elif self.final_tg is None:
            return "merged_times"
        else:
            return "final"

    def get_annotator_status(self, annotator: 'Annotator'):
        if self.current_step == self.Steps.MERGING_TIMES:
            return {**super().get_annotator_status(annotator),
                    "frontiers_merge_table": [error.to_msg() for error
                                              in self.times_conflicts.to_merge_conflicts_errors()]}
        else:
            return super().get_annotator_status(annotator)

    def process_ref(self, textgrid: str):
        """Handles the submission of a textgrid sent by the reference annotator"""
        if self.merged_tg is None:
            # it's a completed textgrid
            tg = SingleAnnotatorTextGrid.from_textgrid_str(textgrid, [self.reference], self)
            tg.check()
            if not error_log.has_errors:
                self.ref_tg = tg
                if self.target_tg is not None:
                    error_log.flush()
                    merged_tg = MergedAnnotsTextGrid.from_ref_and_target(self.ref_tg, self.target_tg)
                    if not error_log.has_errors:
                        self.merged_tg = merged_tg
                        self.notify_merged_ready(self.target)

        elif self.merged_tg is None and self.target_tg is not None:
            tg = SingleAnnotatorTextGrid.from_textgrid_str(textgrid, [self.reference], self)
            tg.check()
            if not error_log.has_errors:
                self.ref_tg = tg
                error_log.flush()
                merged_tg = MergedAnnotsTextGrid.from_ref_and_target(self.ref_tg, self.target_tg)
                if not error_log.flush():
                    self.merged_tg = merged_tg
                    self.notify_merged_ready(self.target)

        elif self.merged_annots_tg is None:
            # processing the merged annots textgrid
            tg = MergedAnnotsTextGrid.from_textgrid_str(textgrid, self.annotators, self)
            tg.check()
            if not error_log.has_errors:
                self.merged_annots_tg = tg
                merged_times_tg, self.times_conflicts = tg.gen_merged_times()
                self.merged_times_tg = MergedTimesTextGrid.from_textgrid_obj(merged_times_tg,
                                                                             self.annotators,
                                                                             self)

        else:
            tg = MergedTimesTextGrid.from_textgrid_str(textgrid, self.annotators, self)
            tg.check()
            if not error_log.has_errors:
                final_tg, _ = tg.check_times_merging()
                self.final_tg = SingleAnnotatorTextGrid.from_textgrid_obj(final_tg, self.annotators, self)
                self.is_done = True
                self.finish_time = datetime.now()
                self.notify_done()

    def process_target(self, textgrid: str):
        """Handles the submission of a textgrid sent by the target annotator"""
        if self.merged_tg is None:
            # it's a completed textgrid
            tg = SingleAnnotatorTextGrid.from_textgrid_str(textgrid, self.annotators, self)
            tg.check()
            if not error_log.has_errors:
                self.target_tg = tg
                if self.ref_tg is not None:
                    error_log.flush()
                    merged_tg = MergedAnnotsTextGrid.from_ref_and_target(self.ref_tg, self.target_tg)
                    if not error_log.has_errors:
                        self.merged_tg = merged_tg
                        self.notify_merged_ready(self.reference)

        elif self.merged_tg is None and self.reference is not None:
            tg = SingleAnnotatorTextGrid.from_textgrid_str(textgrid, [self.target_tg], self)
            tg.check()
            if not error_log.has_errors:
                self.ref_tg = tg
                error_log.flush()
                merged_tg = MergedAnnotsTextGrid.from_ref_and_target(self.ref_tg, self.target_tg)
                if not error_log.flush():
                    self.merged_tg = merged_tg
                    self.notify_merged_ready(self.reference)

    def submit_textgrid(self, textgrid: str, annotator: 'Annotator'):
        if self.is_locked:
            return

        error_log.flush()
        if annotator == self.reference:
            self.process_ref(textgrid)
        elif annotator == self.target:
            self.process_target(textgrid)

        self.cascade_save()
        self._log_upload(textgrid, annotator, not error_log.has_errors)

    def validate_textgrid(self, textgrid: str, annotator: 'Annotator'):
        if self.is_locked:
            return

        error_log.flush()
        tg: BaseTextGridDocument = None
        if annotator == self.reference:
            if self.merged_tg is None:
                # it's a completed textgrid
                tg = SingleAnnotatorTextGrid.from_textgrid_str(textgrid, [self.reference], self)

            elif self.merged_annots_tg is None:
                # processing the merged annots textgrid
                tg = MergedAnnotsTextGrid.from_textgrid_str(textgrid, self.annotators, self)

            elif self.merged_times_tg is not None and self.final_tg is None:
                # the times haven't been merged yet
                tg = MergedTimesTextGrid.from_textgrid_str(textgrid, self.annotators, self)
            else:
                # it's the final textgrid
                tg = SingleAnnotatorTextGrid.from_textgrid_str(textgrid, self.annotators, self)
        elif annotator == self.target:
            # only one possible textgrid to validate
            tg = SingleAnnotatorTextGrid.from_textgrid_str(textgrid, [self.target_tg], self)
        else:
            return

        tg.check()
        self._log_upload(textgrid, annotator, not error_log.has_errors)


from .users import Annotator
from .textgrids import BaseTextGridDocument
# TODO :check that all stuff that should be delete is deleted
BaseTask.register_delete_rule(Annotator, 'assigned_tasks', PULL)
BaseTask.register_delete_rule(BaseTextGridDocument, 'task', NULLIFY)