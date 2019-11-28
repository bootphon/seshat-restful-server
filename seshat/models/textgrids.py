import re
from collections import Counter
from copy import deepcopy
from datetime import datetime
from statistics import mean
from typing import Tuple, Set
from typing import Union, List

from mongoengine import Document, ReferenceField, ListField, FileField, DateTimeField, BooleanField
from textgrid import Interval, TextGrid, IntervalTier

from .errors import error_log
from .tg_checking import TextGridCheckingScheme
from ..utils import open_str_textgrid, tg_to_str, consecutive_couples


class BaseTextGridDocument(Document):
    textgrid_file = FileField(required=True)
    task = ReferenceField('BaseTask')
    checking_scheme: TextGridCheckingScheme = ReferenceField(TextGridCheckingScheme)
    creators: List['User'] = ListField(ReferenceField('User'))
    creation_time = DateTimeField(default=datetime.now, required=True)
    meta = {'allow_inheritance': True,
            'abstract': True}

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._textgrid_obj: TextGrid = None

    @classmethod
    def from_textgrid(cls, tg: Union[TextGrid,str],
                      creators: List['Annotator'],
                      task: 'BaseTask'):
        if task is not None:
            checking_scheme = task.campaign.checking_scheme
        else:
            checking_scheme = None
        if isinstance(tg, TextGrid):
            tg_file = tg_to_str(tg).encode(encoding='utf-8')
        elif isinstance(tg, str):
            tg_file = tg.encode('utf-8')
        else:
            raise TypeError("Unsupported textgrid object type %s")
        return cls(textgrid_file=tg_file, task=task, creators=creators,
                   checking_scheme=checking_scheme)

    @property
    def textgrid(self):
        if self._textgrid_obj is None:
            # TODO : make sure to catch a potential textgrid parsing error somewhere
            self._textgrid_obj = open_str_textgrid(self.textgrid_file.read().decode("utf-8").strip())
        return self._textgrid_obj

    @textgrid.setter
    def textgrid(self, tg: Union[TextGrid, str]):
        if isinstance(tg, str):
            self.textgrid_file.put(tg.encode("utf-8"))
        elif isinstance(tg, TextGrid):
            self._textgrid_obj = tg
            self.textgrid_file.put(tg_to_str(tg).encode("utf-8"))
        else:
            raise ValueError("Expecting textgrid in string format or as a TextGrid object")

    def to_str(self):
        return self.textgrid_file.read().decode("utf-8")

    def check(self):
        raise NotImplemented()

    @property
    def task_tg_msg(self):
        return {
            "id": self.id,
            "creators": [annotator.short_profile for annotator in self.creators],
            "created": self.creation_time
        }


class LoggedTextGrid(BaseTextGridDocument):
    meta = {"collection": "logged_textgrid"}


class SingleAnnotatorTextGrid(BaseTextGridDocument):

    def check_duplicate_tiers(self):
        # checking for any tier duplicate
        names_counter = Counter(self.textgrid.getNames())
        for tier_name, count in names_counter.items():
            if count > 1:
                error_log.log_structural("Duplicate tier name:  %s" % tier_name)

    def check_scheme_tiers(self):
        tg_tier_names = set(self.textgrid.getNames())

        # checking that required tiers are all here
        required_tiers = set(self.checking_scheme.required_tiers_names)
        missing_tiers = required_tiers - set(self.textgrid.getNames())
        if missing_tiers:
            error_log.structural("The tiers %s are missing in the TextGrid file" % " ,".join(missing_tiers))

        # removing all tiers that are referenced in the scheme
        tg_tier_names -= set(self.checking_scheme.all_tiers_names)

        # remaining tiers are invalid
        if tg_tier_names:
            error_log.log_structural("The tiers %s are unexpected (and thus invalid)" % ", ".join(tg_tier_names))

    def check_annotations(self):
        valid_tiers = set(self.checking_scheme.all_tiers_names) & set(self.textgrid.getNames())
        for tier_name in valid_tiers:
            tier_scheme = self.checking_scheme.get_tier_scheme(tier_name)
            tier_scheme.check_tier(self.textgrid.getFirst(tier_name))

    def check(self):
        self.check_duplicate_tiers()
        if self.checking_scheme:
            self.check_scheme_tiers()
            self.check_annotations()


class DoubleAnnotatorTextGrid(SingleAnnotatorTextGrid):
    reference = ReferenceField('Annotator')
    target = ReferenceField('Annotator')


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


class MergedAnnotsTextGrid(DoubleAnnotatorTextGrid):
    TOP_GROUP_SUFFIX = "-ref"
    BOTTOM_GROUP_SUFFIX = "-target"

    DIFF_THRESHOLD = 0.1  # in seconds

    @classmethod
    def from_ref_and_target(cls, ref_tg: BaseTextGridDocument,
                            target_tg: BaseTextGridDocument):
        """Simply interweaves the ref and target into one tg for annotations
                merging"""
        # checking first if both TG have the same amount of tiers, and the same names
        ref_names = sorted(ref_tg.textgrid.getNames())
        target_names = sorted(target_tg.textgrid.getNames())
        if len(ref_names) != len(target_names):
            error_log.structural("The reference and target annotator's textgrids don't have the same amount of Tiers "
                                 "(%i for the reference, %i for the target)"
                                 % (len(ref_names), len(target_names)))
            return

        if ref_names != target_names:
            # TODO: maybe make this more helpful
            error_log.structural("The names of some of the tiers in the reference and target textgrids don't match")
            return

         # TODO : add support for empty tiers deletion
        assert ref_tg.task == target_tg.task
        merged_tg = TextGrid(name=ref_tg.textgrid.name,
                             minTime=ref_tg.textgrid.minTime,
                             maxTime=ref_tg.textgrid.maxTime)
        for tier_name in ref_tg.textgrid.getNames():
            ref_tier: IntervalTier = deepcopy(ref_tg.textgrid.getFirst(tier_name))
            target_tier: IntervalTier = deepcopy(target_tg.textgrid.getFirst(tier_name))
            ref_tier.name = tier_name + "-ref"
            target_tier.name = tier_name + "-target"
            merged_tg.append(ref_tier)
            merged_tg.append(target_tier)
        new_doc = cls.from_textgrid(merged_tg, ref_tg.creators + target_tg.creators, ref_tg.task)
        return new_doc

    @property
    def suffixed_tier_names(self) -> Set[str]:
        names = set()
        for suffix in (self.TOP_GROUP_SUFFIX, self.BOTTOM_GROUP_SUFFIX):
            for name in set(self.checking_scheme.all_tiers_names):
                names.add(name + suffix)
        return names

    def check_tiers_matching(self):
        """Checks that all tiers match either suffixes, and that tier radicals are found
        twice (one for top TOP_GROUP_SUFFIX, one for BOTTOM_GROUP_SUFFIX)"""
        pass

    def check_scheme_tiers(self):
        """Checks that the tier radicals against the """
        tier_names_set: Set[str] = set(self.textgrid.getNames())

        # checking that required tiers are all there for both suffixes
        for suffix in (self.TOP_GROUP_SUFFIX, self.BOTTOM_GROUP_SUFFIX):
            req_tiers_suffixed = set(name + suffix for name in set(self.checking_scheme.required_tiers_names))
            missing_tiers = req_tiers_suffixed - set(self.textgrid.getNames())
            if missing_tiers:
                error_log.structural("The tiers %s are missing" % " ,".join(missing_tiers))
            tier_names_set -= req_tiers_suffixed

        # filtering out valid tiers to weed out potential invalid tiers names
        tier_names = set(self.textgrid.getNames())
        all_tiers_suffixed = set(name + suffix for name in set(self.checking_scheme.all_tiers_names))
        tier_names -= all_tiers_suffixed

        # remaining tiers are invalid
        if tier_names:
            error_log.log_structural("The tiers %s are unexpected (and thus invalid)" % ", ".join(tier_names))
        else:
            # checking that both top and bottom have the same tiers
            no_suffix = set(re.sub("(%s|%s)" % (self.TOP_GROUP_SUFFIX, self.BOTTOM_GROUP_SUFFIX), "", name)
                            for name in self.textgrid.getNames())
            tier_names_set = set(self.textgrid.getNames())
            for no_suffix_name in no_suffix:
                suffixed_top = no_suffix_name + self.TOP_GROUP_SUFFIX
                suffixed_bottom = no_suffix_name + self.BOTTOM_GROUP_SUFFIX
                if suffixed_top not in tier_names_set:
                    error_log.log_structural("The %s tier is missing" % suffixed_top)
                elif suffixed_bottom not in tier_names_set:
                    error_log.log_structural("The %s tier is missing" % suffixed_bottom)

    def check_times_merging(self):
        """Checks that paired tiers can be merged together. Outputs the partially merged textgrid as
        well as the merge conflicts."""
        from .tasks import MergeResults
        merged_times_tg = TextGrid(
            name=self.textgrid.name,
            maxTime=self.textgrid.maxTime,
            minTime=self.textgrid.minTime)
        merge_results = MergeResults()
        for tier in self.checking_scheme.all_tiers_names:
            merged_tier_name = tier + self.TOP_GROUP_SUFFIX
            target_tier_name = tier + self.BOTTOM_GROUP_SUFFIX
            merged_tier = self.textgrid.getFirst(merged_tier_name)
            target_tier = self.textgrid.getFirst(target_tier_name)
            # in case either tier is not present, we just skip this merge
            if merged_tier is None or target_tier is None:
                continue

            times_merged_tier, tier_merge = self.merge_tiers(merged_tier, target_tier)
            merge_results.tiers_merges.append(tier_merge)
            times_merged_tier.name = tier
            merged_times_tg.append(times_merged_tier)

        # logging conflicts as errors that could be displayed to the
        # annotator (in case of merge attempt)
        for conflict in merge_results.to_merge_conflicts_errors():
            error_log.log_merge(conflict)
        return merged_times_tg, merge_results

    def check_annotations_matching(self):
        """Checks that pairs of target/ref tiers have the same number of annotations,
        and that those annotations are the same"""
        for tier in self.checking_scheme.all_tiers_names:
            ref_tier_name = tier + self.TOP_GROUP_SUFFIX
            target_tier_name = tier + self.BOTTOM_GROUP_SUFFIX
            ref_tier = self.textgrid.getFirst(ref_tier_name)
            target_tier = self.textgrid.getFirst(target_tier_name)
            # checking that both tier exist
            if target_tier is None or ref_tier is None:
                continue

            if not len(ref_tier) == len(target_tier):
                error_log.log_structural("The tiers %s and %s don't have the same number of annotations"
                                         % (ref_tier_name, target_tier_name))

            for i, (ref_int, target_int) in enumerate(
                    zip(ref_tier, target_tier)):
                if ref_int.mark != target_int.mark:
                    error_log.log_mismatch(ref_tier_name, target_tier_name, i, ref_int, target_int)
                    break

    @staticmethod
    def to_frontiers(tier: IntervalTier):
        return [
            Frontier(left, right) for right, left in consecutive_couples(tier)
        ]

    @classmethod
    def merge_tiers(cls, tier_a: IntervalTier, tier_b: IntervalTier) -> Tuple[IntervalTier, 'TierMerge']:
        from .tasks import TierMerge, FrontierMerge
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

    def gen_merged_times(self):
        """Merges times"""
        merged_times_tg, merge_results = self.check_times_merging()
        new_tg = TextGrid(name=merged_times_tg.name,
                          maxTime=merged_times_tg.maxTime,
                          minTime=merged_times_tg.minTime)

        for tier_name in self.checking_scheme.all_tiers_names:
            merged_tier: IntervalTier = deepcopy(merged_times_tg.getFirst(tier_name))
            target_tier: IntervalTier = deepcopy(self.textgrid.getFirst(tier_name + "-target"))
            merged_tier.name = tier_name + "-merged"
            new_tg.append(merged_tier)
            new_tg.append(target_tier)

        return new_tg, merge_results

    def check_annotations(self):
        # getting only validated tiers
        validated_tiers = set(self.checking_scheme.all_tiers_names)
        for tier_name in self.textgrid.getNames():
            # removing suffix from tier, and if that radical isn't defined in the scheme, ignore it
            no_suffix_name = re.sub("(%s|%s)" % (self.TOP_GROUP_SUFFIX, self.BOTTOM_GROUP_SUFFIX),
                                    "", tier_name)
            if no_suffix_name not in validated_tiers:
                continue
            tier_scheme = self.checking_scheme.get_tier_scheme(no_suffix_name)
            tier_scheme.check_tier(self.textgrid.getFirst(tier_name))

    def check(self):
        self.check_duplicate_tiers()
        self.check_tiers_matching()
        if self.checking_scheme:
            self.check_scheme_tiers()
            self.check_annotations()
        self.check_annotations_matching()


class MergedTimesTextGrid(MergedAnnotsTextGrid):
    TOP_GROUP_SUFFIX = "-merged"
    BOTTOM_GROUP_SUFFIX = "-target"

    def check(self):
        self.check_duplicate_tiers()
        self.check_tiers_matching()
        if self.checking_scheme:
            self.check_scheme_tiers()
            self.check_annotations()
        self.check_annotations_matching()
        self.check_times_merging()

