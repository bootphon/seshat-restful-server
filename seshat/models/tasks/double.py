from datetime import datetime
from enum import Enum
from typing import Dict, Optional

from mongoengine import (EmbeddedDocument, FloatField, IntField, BooleanField, StringField, EmbeddedDocumentListField,
                         ReferenceField, EmbeddedDocumentField, MapField, signals)

from ..commons import notif_dispatch
from ..errors import MergeConflictsError, error_log
from ..tasks.base import BaseTask
from ..textgrids import MergedAnnotsTextGrid, BaseTextGridDocument, SingleAnnotatorTextGrid, MergedTimesTextGrid
from ..tg_checking import TextGridCheckingScheme


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
    ref_tg = ReferenceField(BaseTextGridDocument)
    # fully annotated textgrid from the target annotator
    target_tg = ReferenceField(BaseTextGridDocument)
    # target and ref annotated tg's stacked one onto another, for annotation
    # merging
    merged_tg: MergedAnnotsTextGrid = ReferenceField(MergedAnnotsTextGrid)
    times_conflicts = EmbeddedDocumentField(MergeResults)
    # target and ref still stacked, but all annotations are the same
    merged_annots_tg: MergedAnnotsTextGrid = ReferenceField(MergedAnnotsTextGrid)
    # times that could be merged automatically are merged, annotators have to
    # agree on frontiers that are too "far away" from each other
    merged_times_tg: MergedTimesTextGrid = ReferenceField(MergedTimesTextGrid)

    # gamma values for each tier.
    tiers_gamma: Dict[str, float] = MapField(FloatField())

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
        Steps.MERGING_TIMES: "Merging Times",
        Steps.DONE: "Done"
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
        """Join the reference annotator now, so you can (together) find an agreement based on 
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
            object_id=str(self.id),
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

    @property
    def allow_starter_zip_dl(self) -> bool:
        return self.current_step in (self.Steps.PARALLEL, self.Steps.PENDING, self.Steps.TIERS_AGREEMENT)

    @property
    def can_compute_gamma(self) -> bool:
        return self.current_step.value >= self.Steps.MERGING_ANNOTS.value

    def allow_file_upload(self, annotator: 'Annotator') -> bool:
        if annotator == self.reference:
            return True
        elif annotator == self.target:
            return self.current_step in (self.Steps.PENDING, self.Steps.PARALLEL, self.Steps.TIERS_AGREEMENT)

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
        double_annot_data = {
            "reference": self.reference.short_profile,
            "target": self.target.short_profile,
            "current_user_role": 'reference' if annotator == self.reference else 'target'
        }

        if self.current_step == self.Steps.MERGING_TIMES:
            double_annot_data["frontiers_merge_table"] = [error.to_msg() for error
                                                          in self.times_conflicts.to_merge_conflicts_errors()]

        return {**super().get_annotator_status(annotator), "double_annot_data": double_annot_data}

    def process_ref(self, textgrid: str):
        """Handles the submission of a textgrid sent by the reference annotator"""
        if self.merged_tg is None:
            # it's a completed single-annotator textgrid
            tg = SingleAnnotatorTextGrid.from_textgrid(textgrid, [self.reference], self)
            tg.check()
            if not error_log.has_errors:
                self.ref_tg = tg
                if self.target_tg is not None:
                    error_log.flush()
                    merged_tg = MergedAnnotsTextGrid.from_ref_and_target(self.ref_tg, self.target_tg)
                    if not error_log.has_errors:
                        self.merged_tg = merged_tg
                        self.notify_merged_ready(self.target)
                        self.tiers_gamma = None
                        self.campaign.update_stats(gamma_only=True)

        elif self.merged_annots_tg is None:
            # processing the merged annots textgrid
            tg = MergedAnnotsTextGrid.from_textgrid(textgrid, self.annotators, self)
            tg.check()
            if not error_log.has_errors:
                self.merged_annots_tg = tg
                merged_times_tg, self.times_conflicts = tg.gen_merged_times()
                self.merged_times_tg = MergedTimesTextGrid.from_textgrid(merged_times_tg,
                                                                         self.annotators,
                                                                         self)

        else:
            tg = MergedTimesTextGrid.from_textgrid(textgrid, self.annotators, self)
            tg.check()
            if not error_log.has_errors:
                final_tg, _ = tg.check_times_merging()
                self.final_tg = SingleAnnotatorTextGrid.from_textgrid(final_tg, self.annotators, self)
                self.is_done = True
                self.finish_time = datetime.now()
                if self.final_tg is None:
                    self.notify_done()
                    self.campaign.update_stats()

    def process_target(self, textgrid: str):
        """Handles the submission of a textgrid sent by the target annotator"""
        if self.merged_tg is None:
            # it's a completed textgrid
            tg = SingleAnnotatorTextGrid.from_textgrid(textgrid, self.annotators, self)
            tg.check()
            if not error_log.has_errors:
                self.target_tg = tg
                if self.ref_tg is not None:
                    error_log.flush()
                    merged_tg = MergedAnnotsTextGrid.from_ref_and_target(self.ref_tg, self.target_tg)
                    if not error_log.has_errors:
                        self.merged_tg = merged_tg
                        self.notify_merged_ready(self.reference)
                        self.tiers_gamma = None
                        self.campaign.update_stats(gamma_only=True)

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
                tg = SingleAnnotatorTextGrid.from_textgrid(textgrid, [self.reference], self)

            elif self.merged_annots_tg is None:
                # processing the merged annots textgrid
                tg = MergedAnnotsTextGrid.from_textgrid(textgrid, self.annotators, self)

            elif self.merged_times_tg is not None and self.final_tg is None:
                # the times haven't been merged yet
                tg = MergedTimesTextGrid.from_textgrid(textgrid, self.annotators, self)
            else:
                # it's the final textgrid
                tg = SingleAnnotatorTextGrid.from_textgrid(textgrid, self.annotators, self)
        elif annotator == self.target:
            # only one possible textgrid to validate
            tg = SingleAnnotatorTextGrid.from_textgrid(textgrid, [self.target_tg], self)
        else:
            return

        tg.check()
        self._log_upload(textgrid, annotator, not error_log.has_errors)

    def compute_gamma(self):
        checking_scheme: TextGridCheckingScheme = self.campaign.checking_scheme
        self.tiers_gamma = {}
        for tier_name, tier_scheme in checking_scheme.tiers_specs.items():
            try:
                gamma_val = tier_scheme.compute_gamma(self.ref_tg.textgrid,
                                                      self.target_tg.textgrid)
            except Exception as err:
                print(f'Got error "{type(err)} : {str(err)}" on task for file {self.data_file.name}, '
                      f'while computing gamma for tier {tier_name}.')
                continue
            else:
                if gamma_val is not None:
                    self.tiers_gamma[tier_name] = gamma_val

        if not self.tiers_gamma:
            raise ValueError("Couldn't compute gamma for ")


signals.post_delete.connect(BaseTask.post_delete_cleanup, sender=DoubleAnnotatorTask)
signals.post_save.connect(BaseTask.post_save, sender=DoubleAnnotatorTask)
