from collections import defaultdict
from typing import List, Dict

from dataclasses import dataclass
from textgrid import Interval


class BaseTextGridError:

    def to_msg(self) -> Dict:
        pass


@dataclass
class TextGridAnnotationError(BaseTextGridError):
    """Some annotation in the textgrid isn't right"""
    tier: str
    annot_idx: int
    interval: Interval
    msg: str

    def to_msg(self) -> Dict:
        return {
            "tier": self.tier,
            "index": self.annot_idx,
            "annotation": self.interval.mark,
            "start": float(self.interval.minTime),
            "end": float(self.interval.maxTime),
            "msg": self.msg
        }


@dataclass
class TextgridAnnotationMismatch(BaseTextGridError):
    ref_tier: str
    target_tier: str
    annot_idx: int
    ref_interval: Interval
    target_interval: Interval

    def to_msg(self) -> Dict:
        return {
            "ref_tier": self.ref_tier,
            "target_tier": self.target_tier,
            "index": self.annot_idx,
            "ref_annot": self.ref_interval.mark,
            "target_annot": self.target_interval.mark,
        }


@dataclass
class MergeConflictsError(BaseTextGridError):
    """Merge error when trying to merge frontiers"""
    tier_a: str
    tier_b: str
    time_a: float
    time_b: float
    index_before: int

    def to_msg(self) -> Dict:
        from .textgrids import MergedAnnotsTextGrid
        return {
            "tier_a": self.tier_a,
            "tier_b": self.tier_b,
            "time_a": self.time_a,
            "time_b": self.time_b,
            "index_before": self.index_before,
            "index_after": self.index_before + 1,
            "threshold": MergedAnnotsTextGrid.DIFF_THRESHOLD
        }


@dataclass
class TextGridStructuralError(BaseTextGridError):
    """Something is wrong with the textgrid as a whole"""
    msg: str

    def to_msg(self):
        return {"msg": self.msg}


class ErrorsLog:

    def __init__(self):
        self.structural: List[TextGridStructuralError] = list()
        self.annot: Dict[str, List[TextGridAnnotationError]] = defaultdict(list)
        self.mismatch: List[TextgridAnnotationMismatch] = list()
        self.timing: List[MergeConflictsError] = list()

    def log_structural(self, msg: str):
        self.structural.append(TextGridStructuralError(msg))

    def log_mismatch(self, ref_tier: str, target_tier: str, annot_idx: int,
                     ref_interval: Interval, target_interval):
        self.mismatch.append(TextgridAnnotationMismatch(
            ref_tier, target_tier, annot_idx, ref_interval, target_interval
        ))

    def log_merge(self, merge_conflict: MergeConflictsError):
        self.timing.append(merge_conflict)

    def log_annot(self, tier: str, annot_idx: int, interval: Interval, msg: str):
        self.annot[tier].append(TextGridAnnotationError(tier, annot_idx, interval, msg))

    def flush(self):
        self.structural = list()
        self.annot = defaultdict(list)
        self.mismatch = list()
        self.timing = list()

    @property
    def has_errors(self) -> bool:
        return any(bool(collection) for collection
                   in [self.structural, self.annot, self.mismatch, self.timing])

    def to_errors_summary(self):
        return {
            "has_errors": self.has_errors,
            "structural": [error.to_msg() for error in self.structural],
            "annot_mismatch": [error.to_msg() for error in self.mismatch],
            "time_conflict": [error.to_msg() for error in self.timing],
            "annot": {tier: [error.to_msg() for error in errors]
                      for tier, errors in self.annot.items()}
        }


error_log = ErrorsLog()
