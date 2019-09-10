import zipfile
from copy import deepcopy
from datetime import date
from io import BytesIO, StringIO
from pathlib import Path
from typing import Dict, List

import ffmpeg
from flask import current_app as app, url_for
from flask_login import current_user
from mongoengine import StringField, ReferenceField, DoesNotExist, \
    EmbeddedDocument, FloatField, IntField, BooleanField, \
    EmbeddedDocumentListField, EmbeddedDocumentField
from textgrid import TextGrid, IntervalTier

from tools.models.commons import DBError, notif_dispatch
from tools.models.tasks import BaseTask
from tools.textgrid_checking.basal_voice_tg import TaskTextGridChecker, \
    TaskAnnotationChecker, MergedTimesTextGridChecker, \
    MergedAnnotTextgridChecker
from tools.textgrid_checking.common import MergeConflictsError
from tools.utils import tg_to_str, open_str_textgrid


class BasalVoiceTask(BaseTask):
    # Only contains one Tier ("Task")  of the audio file's length
    # with nothing in it.
    template_tg = StringField(required=True)
    # the final annotated file, with 4 tiers
    final_tg = StringField()

    # Displayed when the initial template is to be annotated (which,
    # once filled, becomes the task_tg)
    INITIAL_TEMPLATE_INSTRUCTIONS = """Pour compléter cette étape, annote 
    uniquement les tâches sur l'unique Tiers du fichier TextGrid, 
    puis soumets-le pour le valider, et pouvoir passer à l'étape suivante."""

    # Displayed when the task template is to be annotated (to produce a fully
    # annotated textgrid)
    TASK_TEMPLATE_INSTRUCTIONS = """Pour compléter cette étape, il faut 
    remplir les annotations des 3 Tiers restants, sans modifier les bornes 
    de tâches définies par l'étape précédente"""

    @classmethod
    def create_task_template(cls, data_file: str):
        duration = float(ffmpeg.probe(data_file)["format"]["duration"])
        new_tg = TextGrid(name=data_file,
                          minTime=0.0,
                          maxTime=duration)
        new_tier = IntervalTier(name="Task",
                                minTime=0.0,
                                maxTime=duration)
        new_tg.append(new_tier)
        return tg_to_str(new_tg)

    @property
    def textgrids(self) -> Dict[str, str]:
        return {"template": self.template_tg,
                "tasks": self.tasks_tg,
                "tasks_template": self.tasks_template_tg,
                "final": self.final_tg}


    @property
    def has_started(self):
        return self.tasks_tg is not None


class BasalVoiceSingleAnnotatorTask(BasalVoiceTask):
    TASK_TYPE = "Annotateur unique"
    annotator = ReferenceField('Annotator', required=True)

    @classmethod
    def create_and_assign(cls, audio_files: List[str], campaign: 'Campaign',
                          assigner: 'Admin', deadline: date,
                          annotator_username: str):
        from .users import Annotator
        try:
            annotator = Annotator.objects.get(username=annotator_username)
        except DoesNotExist:
            raise DBError("L'utilisateur %s n'existe pas.")

        for file in audio_files:
            actual_filepath = (
                    Path(app.config["CAMPAIGNS_FILES_ROOT"]) / Path(file))
            task_template = cls.create_task_template(str(actual_filepath))
            new_task = cls(
                campaign=campaign.id,
                assigner=assigner.id,
                data_file=file,
                deadline=deadline,
                annotator=annotator.id,
                template_tg=task_template)
            new_task.save()
            campaign.tasks.append(new_task.id)
            annotator.assigned_tasks.append(new_task.id)
        cls.notify_assign([annotator], campaign)
        campaign.save()
        annotator.save()

    @property
    def annotators(self):
        return [self.annotator]

    @property
    def current_instructions(self):
        if self.tasks_tg is None:
            return self.INITIAL_TEMPLATE_INSTRUCTIONS

        else:
            return self.TASK_TEMPLATE_INSTRUCTIONS

    @property
    def current_tg_template(self):
        if self.tasks_tg is None:
            return "template"
        elif self.final_tg is None:
            return "tasks_template"
        else:
            return "final"

    def get_starter_zip(self) -> bytes:
        buffer = BytesIO()
        with zipfile.ZipFile(buffer, "w", zipfile.ZIP_STORED) as zfile:
            zip_folder: str = self.name
            textgrid_archname = (Path(zip_folder) /
                                 Path(Path(self.data_file).stem + ".TextGrid"))
            zfile.writestr(
                str(textgrid_archname), self.template_tg)

        return buffer.getvalue()

    def submit_textgrid(self, textgrid: str, annotator: 'Annotator'):
        if self.is_locked:
            return

        if self.tasks_tg is None:
            checker = TaskTextGridChecker(textgrid)
            checker.validate()
            if checker.is_valid():
                self.tasks_tg = textgrid
                self.tasks_template_tg = checker.get_4_tiers_textgrid()
        else:
            checker = TaskAnnotationChecker(textgrid)
            checker.validate()
            if checker.is_valid():
                self.final_tg = textgrid
                self.notify_done()

        self.save()
        self._log_upload(textgrid, annotator, checker.errors)
        if checker.is_valid():
            return None, checker.warnings
        else:
            return checker.errors, checker.warnings

    def validate_textgrid(self, textgrid: str, annotator: 'Annotator'):
        if self.is_locked:
            return

        if self.tasks_tg is None:
            checker = TaskTextGridChecker(textgrid)
        else:
            checker = TaskAnnotationChecker(textgrid)

        checker.validate()

        self._log_upload(textgrid, annotator, checker.errors)
        if checker.is_valid():
            return None, checker.warnings
        else:
            return checker.errors, checker.warnings


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

    @property
    def merge_conflicts_log(self) -> str:
        log_str = StringIO()
        for error in self.to_merge_conflicts_errors():
            log_str.write(error.msg + "\n")
        return log_str.getvalue()


class BasalVoiceDoubleAnnotatorTask(BasalVoiceTask):
    TASK_TYPE = "Double annotateurs"
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
    # times conflicts could all be merged, this is a regular 4-tier textgrid
    final_tg = StringField()

    WAIT_FOR_OTHER_ANNOTATOR_INSTRUCTIONS = \
        """Attends que l'annotatrice dite '%s' termine son travail d'annotation 
        pour poursuivre."""

    WAIT_FOR_REF_INSTRUCTIONS = \
        """L'annotatrice référence doit d'abord faire l'annotation des tâches 
        des base. Il faut attendre qu'elle ait terminé pour commencer."""

    REF_MERGE_ANNOTS_INSTRUCTIONS = \
        """Il faut maintenant que l'annotatrice dite 'target' te rejoigne pour 
        que vous puissiez vous mettre  d'accord sur le contenu des annotations 
        et sur leur nombre. L'objectif est d'avoir, pour tout les Tiers, 
        le même nombre d'annotations avec la même valeur."""

    TARGET_MERGE_ANNOTS_INSTRUCTIONS = \
        """Rejoins maintenant l'annotatrice référence pour pouvoir, ensemble, 
        se mettre d'accord sur vos annotations respectives. La fusion 
        se fait sur sa machine."""

    REF_MERGE_TIMES_INSTRUCTIONS = \
        """Toujours ensemble avec l'annotatrice target, vous devez faire en 
        sorte que les frontières qui n'ont pas pu être fusionnées 
        (indiquées ci-dessous) soient plus proches (%ims).""" \
        % int(MergedTimesTextGridChecker.DIFF_THRESHOLD * 1000)

    TARGET_MERGE_TIMES_INSTRUCTIONS = \
        """Rejoins maintenant l'annotatrice référence pour pouvoir, 
        ensemble, terminer la fusion des temps. La fusion se fait sur sa 
        machine. Pour que tu puisses l'aider, les frontières à fusionner sont 
        listées ci-dessous. La fusions se fait sur sa machine."""

    @property
    def status(self):
        if not self.is_done:
            if self.ref_tg is None or self.target_tg is None:
                return "Annotations parallèles"
            elif self.merged_annots_tg is None:
                return "Fusion des annots."
            else:
                return "Fusion des temps"
        else:
            return "Terminée"

    @property
    def annotators(self):
        return [self.reference, self.target]

    def notify_task_template(self):
        notif_dispatch(
            message=("L'annotatrice référence a terminé l'annotation des"
                     "tâches sur "
                     "la tâche double-annotateur du fichier %s"
                     % (self.data_file)),
            notif_type="finished",
            url=url_for("annotator_task", task_id=self.id),
            users=[self.target])

    def notify_merged_ready(self, annotator: 'Annotator'):
        notif_dispatch(
            message=("L'autre annotatrice a terminé l'annotation sur "
                     "la tâche double-annotateur du fichier %s"
                     % (self.data_file)),
            notif_type="finished",
            url=url_for("annotator_task", task_id=self.id),
            users=[annotator])

    @property
    def current_instructions(self):
        if current_user._get_current_object() == self.reference:
            if self.ref_tg is None:
                if self.tasks_template_tg is None:
                    return self.INITIAL_TEMPLATE_INSTRUCTIONS
                else:
                    return self.TASK_TEMPLATE_INSTRUCTIONS

            elif self.ref_tg is not None and self.target_tg is None:
                return self.WAIT_FOR_OTHER_ANNOTATOR_INSTRUCTIONS % "Target"

            elif self.merged_annots_tg is None:
                return self.REF_MERGE_ANNOTS_INSTRUCTIONS

            else:
                return self.REF_MERGE_TIMES_INSTRUCTIONS

        else:  # it's the target annotator
            if self.ref_tg is None:
                if self.tasks_template_tg is None:
                    return self.WAIT_FOR_REF_INSTRUCTIONS
                elif self.target_tg is not None:
                    return (self.WAIT_FOR_OTHER_ANNOTATOR_INSTRUCTIONS
                            % "reference")
                else:
                    return self.TASK_TEMPLATE_INSTRUCTIONS

            elif self.merged_annots_tg is None:
                return self.TARGET_MERGE_ANNOTS_INSTRUCTIONS

            else:
                return self.TARGET_MERGE_TIMES_INSTRUCTIONS

    @property
    def current_tg_template(self):
        if self.tasks_tg is None:
            return "template"
        elif self.ref_tg is None:
            return "tasks_template"
        elif self.merged_annots_tg is None:
            return "merged"
        elif self.final_tg is None:
            return "merged_times"
        else:
            return "final"

    def get_starter_zip(self) -> bytes:
        buffer = BytesIO()
        with zipfile.ZipFile(buffer, "w", zipfile.ZIP_STORED) as zfile:
            zip_folder: str = self.name
            if current_user._get_current_object() == self.reference:
                textgrid_archname = (
                        Path(zip_folder) /
                        Path(Path(self.data_file).stem + ".TextGrid"))
                zfile.writestr(str(textgrid_archname), self.template_tg)
            else:
                textgrid_archname = (
                        Path(zip_folder) /
                        Path(Path(self.data_file).stem
                             + "_tasks_template.TextGrid"))
                zfile.writestr(str(textgrid_archname), self.tasks_template_tg)

        return buffer.getvalue()

    @property
    def textgrids(self):
        out = super().textgrids
        out.update({
            "ref": self.ref_tg,
            "target": self.target_tg,
            "merged": self.merged_tg,
            "merged_annots": self.merged_annots_tg,
            "merged_times": self.merged_times_tg,
            "final": self.final_tg,
            "conflicts_log": self.times_conflicts.merge_conflicts_log
            if self.times_conflicts is not None else None
        })
        return out

    @classmethod
    def create_and_assign(cls, audio_files: List[str], campaign: 'Campaign',
                          assigner: 'Admin', deadline: date, ref_username: str,
                          target_username: str):
        if target_username == ref_username:
            raise DBError("L'annotateur référence et cible  "
                          "doivent être différents")

        from .users import Annotator
        try:
            ref_annotator = Annotator.objects.get(username=ref_username)
        except DoesNotExist:
            raise DBError("L'utilisateur %s n'existe pas." % ref_username)
        try:
            target_annotator = Annotator.objects.get(username=target_username)
        except DoesNotExist:
            raise DBError("L'utilisateur %s n'existe pas." % ref_username)

        for file in audio_files:
            actual_filepath = (
                    Path(app.config["CAMPAIGNS_FILES_ROOT"]) / Path(file))
            task_template = cls.create_task_template(str(actual_filepath))
            new_task = cls(
                campaign=campaign.id,
                assigner=assigner.id,
                data_file=file,
                deadline=deadline,
                reference=ref_annotator.id,
                target=target_annotator.id,
                template_tg=task_template)
            new_task.save()
            campaign.tasks.append(new_task.id)
            campaign.save()
            ref_annotator.assigned_tasks.append(new_task.id)
            target_annotator.assigned_tasks.append(new_task.id)
            ref_annotator.save()
        cls.notify_assign([ref_annotator, target_annotator], campaign)
        target_annotator.save()

    def render_merged(self):
        """Simply interwines the ref and target into one tg for annotations
        merging"""
        ref_tg = open_str_textgrid(self.ref_tg)
        target_tg = open_str_textgrid(self.target_tg)
        merged_tg = TextGrid(name=ref_tg.name,
                             maxTime=ref_tg.maxTime,
                             minTime=ref_tg.minTime)
        for tier_name in ref_tg.getNames():
            ref_tier: IntervalTier = deepcopy(ref_tg.getFirst(tier_name))
            target_tier: IntervalTier = deepcopy(target_tg.getFirst(tier_name))
            ref_tier.name = tier_name + "-ref"
            target_tier.name = tier_name + "-target"
            merged_tg.append(ref_tier)
            merged_tg.append(target_tier)
        self.merged_tg = tg_to_str(merged_tg)

    def render_merged_times(self):
        """Merges times"""
        annots_merged_tg = open_str_textgrid(self.merged_annots_tg)
        for tier_name in ("Task", "Patient", "Non-patient", "Sentence"):
            tier: IntervalTier = annots_merged_tg.getFirst(tier_name + "-ref")
            tier.name = tier_name + "-merged"

        times_merger = MergedTimesTextGridChecker(tg_to_str(annots_merged_tg))
        times_merger.check_times_merging()
        self.times_conflicts = times_merger.merge_results
        merged_times_tg = deepcopy(times_merger.merged_times_tg)
        new_tg = TextGrid(name=merged_times_tg.name,
                                   maxTime=merged_times_tg.maxTime,
                                   minTime=merged_times_tg.minTime)

        for tier_name in ("Task", "Patient", "Non-patient", "Sentence"):
            merged_tier: IntervalTier = deepcopy(merged_times_tg
                                                 .getFirst(tier_name))
            target_tier: IntervalTier = deepcopy(annots_merged_tg
                                                 .getFirst(tier_name + "-target"))
            merged_tier.name = tier_name + "-merged"
            new_tg.append(merged_tier)
            new_tg.append(target_tier)
        self.merged_times_tg = tg_to_str(new_tg)

    def process_ref(self, textgrid: str):
        # TODO : do not forget to send notification to all project "followers"
        if self.tasks_tg is None:
            checker = TaskTextGridChecker(textgrid)
            checker.validate()
            if checker.is_valid():
                self.tasks_tg = textgrid
                self.tasks_template_tg = checker.get_4_tiers_textgrid()
            self.notify_task_template()

        elif self.merged_tg is None:
            # it's a completed textgrid
            checker = TaskAnnotationChecker(textgrid)
            checker.validate()
            if checker.is_valid():
                self.ref_tg = textgrid
                if self.target_tg is not None:
                    self.render_merged()
                    self.notify_merged_ready(self.target)

        elif self.merged_annots_tg is None:
            # processing the merged annots textgrid
            checker = MergedAnnotTextgridChecker(textgrid)
            checker.validate()
            if checker.is_valid():
                self.merged_annots_tg = textgrid
                self.render_merged_times()

        else:
            checker = MergedTimesTextGridChecker(textgrid)
            checker.validate()
            if checker.is_valid():
                self.final_tg = tg_to_str(checker.merged_times_tg)
                self.is_done = True
                self.notify_done()

        return checker

    def process_target(self, textgrid: str):
        # TODO : do not forget to send notification to all project "followers"
        if self.merged_tg is None:
            # it's a completed textgrid
            checker = TaskAnnotationChecker(textgrid)
            checker.validate()
            if checker.is_valid():
                self.target_tg = textgrid
                if self.ref_tg is not None:
                    self.render_merged()
                    self.notify_merged_ready(self.reference)
            return checker

    def submit_textgrid(self, textgrid: str, annotator: 'Annotator'):
        if self.is_locked:
            return
        checker = None
        if annotator == self.reference:
            checker = self.process_ref(textgrid)
        elif annotator == self.target:
            checker = self.process_target(textgrid)
            if checker is None:
                return

        self.save()
        self._log_upload(textgrid, annotator, checker.errors)
        if checker.is_valid():
            return None, checker.warnings
        else:
            return checker.errors, checker.warnings

    def validate_textgrid(self, textgrid: str, annotator: 'Annotator'):
        if self.is_locked:
            return

        if annotator == self.reference:
            if self.tasks_tg is None:
                checker = TaskTextGridChecker(textgrid)

            elif self.merged_tg is None:
                # it's a completed textgrid
                checker = TaskAnnotationChecker(textgrid)

            elif self.merged_annots_tg is None:
                # processing the merged annots textgrid
                checker = MergedAnnotTextgridChecker(textgrid)

            else:
                checker = MergedTimesTextGridChecker(textgrid)
        elif annotator == self.target:
            # only one possible textgrid to validate
            checker = TaskAnnotationChecker(textgrid)
        else:
            return

        checker.validate()

        self._log_upload(textgrid, annotator, checker.errors)
        if checker.is_valid():
            return None, checker.warnings
        else:
            return checker.errors, checker.warnings