from copy import deepcopy
from statistics import mean
from typing import Tuple
from typing import Union

from mongoengine import Document, StringField, ReferenceField, ListField
from tgt import Interval, TextGrid, IntervalTier

from tools.utils import open_str_textgrid, tg_to_str, consecutive_couples


class TextGridField(StringField):

    def validate(self, value):
        # TODO :  check textgrid parsability
        pass


class BaseTextGridDocument(Document):
    textgrid_str = TextGridField(required=True)
    task = ReferenceField('BaseTask', required=False)
    creators = ListField(ReferenceField('Annotator'))
    meta = {'allow_inheritance': True}

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._textgrid_obj: TextGrid = None

    @property
    def textgrid(self):
        if self._textgrid_obj is None:
            # TODO : make sure to catch a potential textgrid parsing error somewhere
            self._textgrid_obj = open_str_textgrid(self.textgrid_str.strip())
        return self._textgrid_obj

    @textgrid.setter
    def textgrid(self, tg: Union[TextGrid, str]):
        if isinstance(tg, str):
            self.textgrid_str = tg
        elif isinstance(tg, TextGrid):
            self._textgrid_obj = tg
            self.textgrid_str = tg_to_str(tg)
        else:
            raise ValueError("Expecting textgrid in string format or as a TextGrid object")

    def check(self):
        raise NotImplemented()


class SingleAnnotatatorTextGrid(BaseTextGridDocument):
    pass


class DoubleAnnotatorTextGrid(BaseTextGridDocument):
    reference = ReferenceField('Annotator')
    target = ReferenceField('Annotator')


class MergedAnnotsTextGrid(DoubleAnnotatorTextGrid):
    """Used to to check the double-stacked merged annotations textgrid.
        Runs the regular annotation checks, but also checks annotations are
        well aligned between corresponding ref and target tiers"""
    REQUIRED_TIERS = {
        "Task-ref", "Patient-ref", "Non-patient-ref", "Sentence-ref",
        "Task-target", "Patient-target", "Non-patient-target",
        "Sentence-target"
    }
    CHECKED_TIERS_RADICALS = ("Sentence", "Non-patient", "Patient")
    TOP_GROUP_SUFFIX = "-ref"
    BOTTOM_GROUP_SUFFIX = "-target"

    def gen_merged_times(self):
        pass


class Frontier:
    def __init__(self, int_left: Interval, int_right: Interval):
        assert int_left is not None and int_right is not None
        # TODO : maybe check that left == right
        self.left = int_left
        self.right = int_right

    @property
    def time(self):
        return self.left.maxTime

    @time.setter
    def time(self, mean: float):
        self.left.maxTime = mean
        self.right.minTime = mean


class MergedTimesTextGrid(MergedAnnotsTextGrid):
    """Checks that times can be safely merged between the two TextGrids,
        on top of all the inherited checks"""

    REQUIRED_TIERS = {
        "Task-merged", "Patient-merged", "Non-patient-merged",
        "Sentence-merged", "Task-target", "Patient-target",
        "Non-patient-target", "Sentence-target"
    }
    TOP_GROUP_SUFFIX = "-merged"
    # TODO : make this parametrized?
    DIFF_THRESHOLD = 0.1  # in seconds

    def __init__(self, textgrid: str):
        super().__init__(textgrid)
        from tools.models.basal_voice import MergeResults
        self.merge_results: MergeResults = None
        self.merged_times_tg: TextGrid = None

    @staticmethod
    def to_frontiers(tier: IntervalTier):
        return [
            Frontier(left, right) for right, left in consecutive_couples(tier)
        ]

    @classmethod
    def merge_tiers(cls,
                    tier_a: IntervalTier,
                    tier_b: IntervalTier) \
            -> Tuple[IntervalTier, 'TierMerge']:
        from tools.models.basal_voice import TierMerge
        from tools.models.basal_voice import FrontierMerge
        new_tier = deepcopy(tier_a)
        frontiers_a = cls.to_frontiers(new_tier)
        frontiers_b = cls.to_frontiers(tier_b)
        tier_merge = TierMerge(tier_a=tier_a.name, tier_b=tier_b.name)

        for i, (front_a, front_b) in enumerate(zip(frontiers_a, frontiers_b)):
            front_merge = FrontierMerge(
                time_a=front_a.time,
                time_b=front_b.time,
                interval_index_before=i,
                interval_index_after=i + 1)
            if abs(front_a.time - front_b.time) > cls.DIFF_THRESHOLD:
                front_merge.could_merge = False
            else:
                front_merge.could_merge = True
                front_merge.merged_time = float(mean((front_a.time,
                                                      front_b.time)))
            tier_merge.frontiers_merge.append(front_merge)

        return new_tier, tier_merge

    def check_times_merging(self):
        from tools.models.basal_voice import MergeResults
        merged_times_tg = TextGrid(
            name=self.textgrid.name,
            maxTime=self.textgrid.maxTime,
            minTime=self.textgrid.minTime)
        task_tier_cpy = deepcopy(self.textgrid.getFirst("Task-merged"))
        task_tier_cpy.name = "Task"
        merged_times_tg.append(task_tier_cpy)
        merge_results = MergeResults()
        for tier in self.CHECKED_TIERS_RADICALS:
            merged_tier_name = tier + self.TOP_GROUP_SUFFIX
            target_tier_name = tier + self.BOTTOM_GROUP_SUFFIX
            merged_tier = self.textgrid.getFirst(merged_tier_name)
            target_tier = self.textgrid.getFirst(target_tier_name)
            times_merged_tier, tier_merge = self.merge_tiers(
                merged_tier, target_tier)
            merge_results.tiers_merges.append(tier_merge)

            times_merged_tier.name = tier
            merged_times_tg.append(times_merged_tier)

        # logging conflicts as errors that could be displayed to the
        # annotator (in case of merge attempt)
        for conflict in merge_results.to_merge_conflicts_errors():
            self.log_error(conflict)
        self.merge_results = merge_results
        self.merged_times_tg = merged_times_tg

    def check(self):
        pass

    def gen_final_textgrid(self) -> TextGrid:
        pass

