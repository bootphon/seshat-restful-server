from typing import List, Dict
from collections import defaultdict

from textgrid import Interval


class TextGridError:
    def __init__(self):
        pass

    @property
    def header(self):
        raise NotImplemented()

    def __repr__(self):
        return self.msg

    def to_dict(self):
        return {"type": str(self.__class__.__name__)}


class TextgridAnnotationError(TextGridError):
    """Some annotation in the textgrid isn't right"""
    icon = "text_format"

    def __init__(self, tier: str, annot_idx: int, interval: Interval,
                 msg: str):
        super().__init__()
        self.tier, self.idx = tier, annot_idx,
        self.interval = interval
        self.msg = msg

    def to_dict(self):
        out = super().to_dict()
        out.update({
            "tier": self.tier,
            "index": self.idx,
            "annotation": self.interval.mark,
            "start": float(self.interval.minTime),
            "end": float(self.interval.maxTime),
            "msg": self.msg
        })
        return out

    @property
    def header(self):
        return (
                "Erreur dans le Tier \"%s\" , annotation n°%i (de %0.3f à %0.3f)" %
                (self.tier, self.idx + 1, self.interval.minTime,
                 self.interval.maxTime))


class PatientAnnotationError(TextgridAnnotationError):

    def __init__(self, tier: str, annot_idx: int, interval: Interval,
                 msg: str, task: str):
        super().__init__(tier, annot_idx, interval, msg)
        self.task = task

    def to_dict(self):
        out = super().to_dict()
        out.update({
            "task": self.task
        })
        return out

    @property
    def header(self):
        return (
                "Erreur d'annotation le Tier \"%s\" , interval n°%i (de %0.3f à %0.3f), pour la tâche %s" %
                (self.tier, self.idx + 1, self.interval.minTime,
                 self.interval.maxTime, self.task))


class TextgridAnnotationMismatch(TextGridError):
    icon = "call_merge"

    def __init__(self, ref_tier: str, target_tier: str, annot_idx: int,
                 ref_interval: Interval, target_interval):
        super().__init__()
        self.ref_tier, self.target_tier = target_tier, ref_tier
        self.idx = annot_idx
        self.ref_inter = ref_interval
        self.target_inter = target_interval

    def to_dict(self):
        out = super().to_dict()
        out.update({
            "ref_tier": self.ref_tier,
            "target_tier": self.target_tier,
            "index": self.idx,
            "ref_annot": self.ref_inter.mark,
            "target_annot": self.target_inter.mark,
            "msg": self.msg
        })
        return out

    @property
    def header(self):
        return ("Erreur de correspondance entre les Tiers \"%s\" et \"%s\" , "
                "annotation n°%i (de %0.3f à %0.3f et de %0.3f à %0.3f)" %
                (self.ref_tier, self.target_tier, self.idx + 1,
                 self.ref_inter.minTime, self.ref_inter.minTime,
                 self.target_inter.minTime, self.target_inter.minTime))

    @property
    def msg(self):
        return ("L'annotation ref '%s' n'est pas égale "
                "à l'annotation target '%s'" % (self.ref_inter.mark,
                                                self.target_inter.mark))


class MergeConflictsError(TextGridError):
    """Error at the merge time step"""
    icon = "call_merge"

    def __init__(self, tier_a: str, tier_b: str, time_a: float, time_b: float,
                 index_before: int):
        self.tier_a, self.tier_b = tier_a, tier_b
        self.time_a, self.time_b = float(time_a), float(time_b)
        self.index_before = index_before
        self.index_after = index_before + 1
        super().__init__()

    def to_dict(self):
        out = super().to_dict()
        out.update({
            "tier_a": self.tier_a,
            "tier_b": self.tier_b,
            "time_a": self.time_a,
            "time_b": self.time_b,
            "index_before": self.index_before,
            "msg": self.msg
        })
        return out

    @property
    def header(self):
        return ("Conflit de fusion entre les Tiers %s et %s, entre les "
                "intervalles %i et %i" % (self.tier_a, self.tier_b,
                                          self.index_before, self.index_after))

    @property
    def msg(self):
        from .basal_voice_tg import MergedTimesTextGridChecker
        max_time = max((self.time_a, self.time_b))
        min_time = min((self.time_a, self.time_b))
        return ("Impossible de fusionner la frontière entre les intervalles "
                "n°%i et n°%i (%fs - %fs > %fs), entre les tiers %s et %s." %
                (self.index_before, self.index_after, max_time, min_time,
                 MergedTimesTextGridChecker.DIFF_THRESHOLD, self.tier_a,
                 self.tier_b))


class TextGridStructuralError(TextGridError):
    """Something is wrong with the textgrid as a whole"""
    icon = "list"

    def __init__(self, msg: str):
        super().__init__()
        self.msg = msg

    def to_dict(self):
        out = super().to_dict()
        out.update({
            "msg": self.msg
        })
        return out

    @property
    def header(self):
        return "Erreur structurelle"


class TextGridWarning:
    def __init__(self, msg: str):
        self.msg = msg

    @property
    def header(self):
        return "Annotation inhabituelle"


class ErrorsLog:

    def __init__(self):
        self.structural: List[TextGridStructuralError] = list()
        self.annot: Dict[str, List[TextgridAnnotationError]] = defaultdict(list)
        self.mismatch: List[TextgridAnnotationMismatch] = list()
        self.timing: List[MergeConflictsError] = list()
        self.warnings: List[TextGridWarning] = list()

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
        self.annot[tier].append(TextgridAnnotationError(tier, annot_idx, interval, msg))

    def warning(self, msg):
        self.warnings.append(TextGridWarning(msg))

    def flush(self):
        self.structural = list()
        self.annot = defaultdict(list)
        self.mismatch = list()
        self.timing = list()
        self.warnings = list()

    @property
    def has_errors(self) -> bool:
        return any(bool(collection) for collection
                   in [self.structural, self.annot, self.mismatch, self.timing])


error_log = ErrorsLog()

