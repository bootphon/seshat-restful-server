from typing import Union, List

from mongoengine import Document, StringField, ReferenceField, ListField, EmailField

from textgrid import TextGrid
from ..textgrid_checking.common import *

from collections import Counter
from copy import deepcopy
from statistics import mean
from typing import List, Tuple

from textgrid import Interval, TextGrid, IntervalTier

from tools.textgrid_checking.common import *
from tools.textgrid_checking.basal_voice_annots import WordsTaskChecker, \
    VowelsTaskChecker, SpontaneousSpeechChecker
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


class BaseBasalVoiceTextGrid(BaseTextGridDocument):

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.errors: List[TextGridError] = []
        self.warnings: List[TextGridWarning] = []

    def log_error(self, error: TextGridError):
        self.errors.append(error)

    def log_warning(self, warning: TextGridWarning):
        self.warnings.append(warning)

    def _check_begin_end(self, tier: str, interval: Interval, index: int):
        """Returns True if this check matches the BEGIN/END annotation.
        Also, reports any eventual errors related to misplacements on
        BEGIN/END"""
        if interval.mark == "BEGIN":
            if index != 0:
                self.log_error(
                    TextgridAnnotationError(
                        tier, index, interval,
                        "L'annotation BEGIN est forcément la première"
                        "dans le Tier"))
            return True
        elif interval.mark == "END":
            if index != len(self.textgrid.getFirst(tier)) - 1:
                self.log_error(
                    TextgridAnnotationError(
                        tier, index, interval,
                        "L'annotation END est nécessairement la dernière "
                        "dans le Tier"))
            return True
        elif index == 0:
            if interval.mark != "BEGIN":
                self.log_error(
                    TextgridAnnotationError(
                        tier, index, interval,
                        "La première annotation du Tier est nécessairement BEGIN"
                    ))
            return True
        elif index == len(self.textgrid.getFirst(tier)) - 1:
            if interval.mark != "END":
                self.log_error(
                    TextgridAnnotationError(
                        tier, index, interval,
                        "La dernière annotation du Tier est nécessairement END"
                    ))
            return True

        return False

    def check_task_tier(self, tier: IntervalTier):
        self.tasks_intervals = []
        tasknames_count = Counter()
        for i, interval in enumerate(tier):
            if self._check_begin_end(tier.name, interval, i):
                continue

            if interval.mark.lower().strip() in VALID_TASKS_NAMES:
                task_name = interval.mark.lower()
                self.tasks_intervals.append((interval.maxTime,
                                             interval.minTime,
                                             task_name))
                tasknames_count.update([task_name])
                if tasknames_count[task_name] > 1:
                    self.log_error(
                        TextgridAnnotationError(
                            tier.name, i, interval,
                            "La tâche \"%s\" ne peut pas être présente "
                            "plus d'une fois"
                        ))
                    return False
            elif interval.mark == "":
                self.log_error(
                    TextgridAnnotationError(
                        tier.name, i, interval,
                        "Impossible de mettre une annotation vide dans ce Tier"
                    ))
                return False
            else:
                self.log_error(
                    TextgridAnnotationError(
                        "Task", i, interval,
                        "L'annotation \"%s\" n'est pas valide pas pour ce tier" %
                        interval.mark))
                return False
        return True

    def is_valid(self) -> bool:
        return len(self.errors) == 0


class TaskOnlyBasalVoiceTextGrid(BaseBasalVoiceTextGrid):
    # in seconds
    TASKS_ACCEPTABLE_DURATIONS = {
        "[a]": 90,
        "L-[a]-[i]-[u]": 150,
        "he ho": 120,
        "1-20": 150,
        "20-1": 150,
        "mois de l'année endroit": 150,
        "mois de l'année envers": 150,
        "les dernières 24h": 360,
        "histoire tristesse": 360,
        "le petit chaperon rouge": 480,
        "histoire colère": 360,
        "le vol du cookie": 360,
        "histoire joie": 360
    }

    def __init__(self, textgrid: str):
        super().__init__(textgrid)

    def check_tasks_order(self, task_tier: IntervalTier):
        """Logs a warning if the tasks are not in the right order"""
        # TODO : use the gestalt/levenstein distance to indicate which of the
        #        tasks are in a wrong order
        annotated_tasks = [interval.mark for interval in task_tier
                           if interval.mark in VALID_TASKS_NAMES]
        valid_order_tasks = [task for task in VALID_TASKS_NAMES
                             if task in annotated_tasks]
        if annotated_tasks != valid_order_tasks:
            self.log_warning(
                TextGridWarning("Les tâches ne sont pas dans le bon ordre.")
            )

    def check_tasks_presence(self, task_tier: IntervalTier):
        valid_tasks = set([interval.mark for interval in task_tier
                           if interval.mark in VALID_TASKS_NAMES])
        missing_tasks = set(VALID_TASKS_NAMES) - valid_tasks
        if missing_tasks:
            self.log_warning(
                TextGridWarning("Les tâches %s manquent dans ce fichier"
                                % " ,".join(missing_tasks))
            )

    def check_tasks_durations(self, task_tier: IntervalTier):
        valid_names = set(self.TASKS_ACCEPTABLE_DURATIONS.keys())
        for interval in task_tier:
            if interval.mark not in valid_names:
                # error for invalid names is being checked elsewhere, we can
                # just skip it here
                continue

            duration = interval.maxTime - interval.minTime
            if duration > self.TASKS_ACCEPTABLE_DURATIONS[interval.mark]:
                self.log_warning(
                    TextGridWarning(
                        "La tâche %s semble trop longue (%i secondes)"
                        % (interval.mark, int(duration)))
                )

    def check(self):
        if self.textgrid is None:
            return

        if ["Task"] != list(self.textgrid.getNames()):
            self.log_error(
                TextGridStructuralError(
                    "Le fichier TextGrid devrait contenir un seul tier Task"))
            return

        self.check_task_tier(self.textgrid.getFirst("Task"))
        self.check_tasks_order(self.textgrid.getFirst("Task"))

    def gen_4_tiers_textgrid(self) -> str:
        new_tg = TextGrid(
            name=self.textgrid.name,
            maxTime=self.textgrid.maxTime,
            minTime=self.textgrid.minTime)
        new_tg.append(self.textgrid.getFirst("Task"))
        for tier_name in ("Sentence", "Patient", "Non-patient"):
            new_tier = IntervalTier(
                name=tier_name, minTime=new_tg.minTime, maxTime=new_tg.maxTime)
            for interval in self.textgrid.getFirst("Task"):
                if interval.mark in ("BEGIN", "END"):
                    new_tier.addInterval(interval)
                else:
                    new_interval = Interval(interval.minTime, interval.maxTime, "")
                    new_tier.addInterval(new_interval)
            new_tg.append(new_tier)

        return tg_to_str(new_tg)


class BasalVoiceTextGrid(BaseBasalVoiceTextGrid):
    REQUIRED_TIERS = {"Task", "Patient", "Non-patient", "Sentence"}
    TIMES_ROUNDING = 3

    ACCEPTABLE_SENTENCE_DURATION = 20

    def _tier_to_points(self, intervals: List[Interval]):
        points = set()
        for interval in intervals:
            points.add(round(interval.maxTime, self.TIMES_ROUNDING))
            points.add(round(interval.minTime, self.TIMES_ROUNDING))
        return points

    @staticmethod
    def get_interval_task(task_tier: IntervalTier, interval: Interval):
        assert interval.mark not in ("BEGIN", "END")

        for task_interval in task_tier:
            if interval in task_interval:
                return task_interval.mark

        raise RuntimeError("All annotations should be contained in a task")

    def check_np_tier(self, tier: IntervalTier):
        for i, interval in enumerate(tier):
            if self._check_begin_end(tier.name, interval, i):
                continue

            if interval.mark not in ("", "NP", "Noi"):
                self.log_error(
                    TextgridAnnotationError(
                        tier.name, i, interval,
                        "Impossible d'avoir autre chose que des "
                        "annotations vides,\"Noi\" ou \"NP\" dans le Tier "
                        "Non-patient"))

    def check_sentence_tier(self, sentence_tier: IntervalTier,
                            patients_tier: IntervalTier,
                            task_tier: IntervalTier):

        patient_points = self._tier_to_points(list(patients_tier))
        previous_interval = None
        for i, interval in enumerate(sentence_tier):
            if self._check_begin_end(sentence_tier.name, interval, i):
                previous_interval = interval
                continue
            if interval.mark not in ("", "S"):
                self.log_error(
                    TextgridAnnotationError(
                        sentence_tier.name, i, interval,
                        "Impossible d'avoir autre chose que des annotations "
                        "vides ou  \"S\" dans le Tier Sentence"))
            elif previous_interval.mark == interval.mark == "":
                inter_task = self.get_interval_task(task_tier, interval)
                prev_inter_task = self.get_interval_task(task_tier,
                                                         previous_interval)
                if inter_task == prev_inter_task:
                    self.log_error(
                        TextgridAnnotationError(
                            sentence_tier.name, i, interval,
                            "Deux annotations vides ne peuvent se suivre dans "
                            "le tier Sentence"))
            if round(interval.minTime, self.TIMES_ROUNDING) \
                    not in patient_points:
                self.log_error(
                    TextgridAnnotationError(
                        sentence_tier.name, i, interval,
                        "La borne inférieure de  l'intervalle n'est pas "
                        "alignée avec une borne du tier Patient"))
            if round(interval.maxTime, self.TIMES_ROUNDING) \
                    not in patient_points:
                self.log_error(
                    TextgridAnnotationError(
                        sentence_tier.name, i, interval,
                        "La borne supérieure de l'intervalle "
                        "n'est pas alignée avec une borne du tier Patient"))
            duration = interval.maxTime - interval.minTime
            if (interval.mark == "S"
                    and duration > self.ACCEPTABLE_SENTENCE_DURATION):
                self.log_warning(
                    TextGridAnnotationWarning(
                        sentence_tier.name, i, interval,
                        "L'annotation S dans le tier %s fait plus "
                        "de %i secondes"
                        % (sentence_tier.name,
                           self.ACCEPTABLE_SENTENCE_DURATION))
                )
            previous_interval = interval

    def check_structure(self):
        tier_names = set(self.textgrid.getNames())
        if len(tier_names) > len(self.REQUIRED_TIERS):
            self.log_warning(
                TextGridWarning("Seul 4 Tiers devraient être présent dans "
                                "le fichier textgrid"))
        missing = self.REQUIRED_TIERS - tier_names
        if missing:
            self.log_error(
                TextGridStructuralError(
                    "Les Tiers %s ne sont pas présent dans le "
                    "fichier textgrid" % ", ".join(missing)))
            return False
        return True

    def check_tasks_alignment(self, task_tier: IntervalTier,
                              other_tiers_names: List[str]):
        """Cuts the Annotations relevant to a task and pass them on to
        be checked by a task checker"""
        other_tiers_points = {
            tier_name: self._tier_to_points(
                list(self.textgrid.getFirst(tier_name)))
            for tier_name in other_tiers_names
        }
        for i, interval in enumerate(task_tier):
            for tier_name, tier_points in other_tiers_points.items():
                if round(interval.minTime, self.TIMES_ROUNDING) \
                        not in tier_points:
                    self.log_error(
                        TextgridAnnotationError(
                            task_tier.name, i, interval,
                            "La borne inférieure de l'intervalle "
                            "n'est pas alignée avec une borne du tier "
                            "%s" % tier_name))
                if round(interval.minTime, self.TIMES_ROUNDING) \
                        not in tier_points:
                    self.log_error(
                        TextgridAnnotationError(
                            task_tier.name, i, interval,
                            "La borne supérieure de l'intervalle "
                            "n'est pas alignée avec une borne du tier "
                            "%s" % tier_name))

    def included_in(self, small: Interval, big: Interval):
        """Does a "soft match" to figure out if small interval is included in
        the big interval"""
        return (round(small.minTime, self.TIMES_ROUNDING) >= round(
            big.minTime, self.TIMES_ROUNDING)
                and round(small.maxTime, self.TIMES_ROUNDING) <= round(
                    big.maxTime, self.TIMES_ROUNDING))

    def _get_task_annotations(self,
                              task_interval: Interval,
                              patients_tier: IntervalTier):
        first_idx = None
        tasks_annots = []
        for i, interval in enumerate(patients_tier):
            if self.included_in(interval, task_interval):
                if interval.mark == "":
                    continue

                if first_idx is None:
                    first_idx = i + 1
                tasks_annots.append(interval)
            else:
                # sentinel condition, used to save some time and prevent
                # looping through all annotations
                if tasks_annots:
                    break
        return tasks_annots, first_idx

    def check_tasks_annotations(self,
                                task_tier: IntervalTier,
                                patients_tier: IntervalTier,
                                sentence_tier: IntervalTier):
        for interval in task_tier:
            # TODO : log error in the right
            task_name = interval.mark.lower().strip()
            if task_name not in VALID_TASKS_NAMES:
                continue

            task_annots, offset = self._get_task_annotations(interval,
                                                             patients_tier)
            if not task_annots:
                self.log_error(
                    TextGridStructuralError(
                        "La tâche \"%s\" n'a pas été annotée (la partie "
                        "correspondante du tier %s est vide)"
                        % (task_name, patients_tier.name))
                )
            if task_name in ("[a]", "l-[a]-[i]-[u]", "he ho"):
                checker = VowelsTaskChecker(task_name)
            elif task_name in ("1-20", "20-1", "mois de l'année endroit",
                               "mois de l'année envers"):
                checker = WordsTaskChecker(task_name)
            else:
                checker = SpontaneousSpeechChecker(task_name)
            errors, _ = checker.validate(task_annots, offset, patients_tier.name)
            for err in errors:
                self.log_error(err)

            # checking "negative" sentence annotations
            if task_name in ("1-20", "20-1", "mois de l'année endroit",
                             "mois de l'année envers"):
                sentence_annots, offset = self._get_task_annotations(interval,
                                                                     sentence_tier)
                #  TODO

    def check_negative_sentence_annotation(self,
                                           task_tier: IntervalTier,
                                           patients_tier: IntervalTier,
                                           sentence_tier: IntervalTier):
        """Checks that annotations not contained in a sentence streches are
        only additions"""
        pass

    def check(self):
        if self.textgrid is None:
            return

        structure_is_ok = self.check_structure()
        if not structure_is_ok:
            return
        if not self.check_task_tier(self.textgrid.getFirst("Task")):
            return
        self.check_tasks_alignment(
            self.textgrid.getFirst("Task"),
            ["Patient", "Sentence", "Non-patient"])
        self.check_sentence_tier(
            self.textgrid.getFirst("Sentence"),
            self.textgrid.getFirst("Patient"),
            self.textgrid.getFirst("Task"))
        self.check_np_tier(self.textgrid.getFirst("Non-patient"))
        self.check_tasks_annotations(self.textgrid.getFirst("Task"),
                                     self.textgrid.getFirst("Patient"),
                                     self.textgrid.getFirst("Sentence"))


class DoubleAnnotatorTextGrid(BasalVoiceTextGrid):
    reference = ReferenceField('Annotator')
    target = ReferenceField('Annotator')


class MergedAnnotsBasalVoiceTextGrid(BasalVoiceTextGrid):
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

    def check_annotations_matching(self):
        for tier in self.CHECKED_TIERS_RADICALS:
            ref_tier_name = tier + self.TOP_GROUP_SUFFIX
            target_tier_name = tier + self.BOTTOM_GROUP_SUFFIX
            ref_tier = self.textgrid.getFirst(ref_tier_name)
            target_tier = self.textgrid.getFirst(target_tier_name)
            if not len(ref_tier) == len(target_tier):
                self.log_error(
                    TextGridStructuralError(
                        "Les deux tiers %s et %s n'ont pas le même nombre "
                        "d'annotations." % (ref_tier_name, target_tier_name)))
                continue

            for i, (ref_int, target_int) in enumerate(
                    zip(ref_tier, target_tier)):
                if ref_int.mark != target_int.mark:
                    self.log_error(
                        TextgridAnnotationMismatch(ref_tier_name,
                                                   target_tier_name, i,
                                                   ref_int, target_int))

    def check(self):
        if self.textgrid is None:
            return

        structure_is_ok = self.check_structure()
        if not structure_is_ok:
            return
        if not self.check_task_tier(self.textgrid.getFirst("Task-ref")):
            return
        if not self.check_task_tier(self.textgrid.getFirst("Task-target")):
            return
        self.check_tasks_alignment(
            self.textgrid.getFirst("Task-ref"),
            ["Patient-ref", "Sentence-ref", "Non-patient-ref"])
        self.check_tasks_alignment(
            self.textgrid.getFirst("Task-target"),
            ["Patient-target", "Sentence-target", "Non-patient-target"])
        self.check_sentence_tier(
            self.textgrid.getFirst("Sentence-ref"),
            self.textgrid.getFirst("Patient-ref"),
            self.textgrid.getFirst("Task-ref"))
        self.check_sentence_tier(
            self.textgrid.getFirst("Sentence-target"),
            self.textgrid.getFirst("Patient-target"),
            self.textgrid.getFirst("Task-target"))
        self.check_np_tier(self.textgrid.getFirst("Non-patient-ref"))
        self.check_np_tier(self.textgrid.getFirst("Non-patient-target"))
        self.check_tasks_annotations(self.textgrid.getFirst("Task-ref"),
                                     self.textgrid.getFirst("Patient-ref"),
                                     self.textgrid.getFirst("Sentence-ref"))
        self.check_tasks_annotations(self.textgrid.getFirst("Task-target"),
                                     self.textgrid.getFirst("Patient-target"),
                                     self.textgrid.getFirst("Sentence-target"))
        self.check_annotations_matching()

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


class MergedTimesBasalVoiceTextGrid(MergedAnnotsBasalVoiceTextGrid):
    """Checks that times can be safely merged between the two TextGrids,
        on top of all the inherited checks"""

    REQUIRED_TIERS = {
        "Task-merged", "Patient-merged", "Non-patient-merged",
        "Sentence-merged", "Task-target", "Patient-target",
        "Non-patient-target", "Sentence-target"
    }
    TOP_GROUP_SUFFIX = "-merged"
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
        if self.textgrid is None:
            return

        structure_is_ok = self.check_structure()
        if not structure_is_ok:
            return
        if not self.check_task_tier(self.textgrid.getFirst("Task-merged")):
            return
        if not self.check_task_tier(self.textgrid.getFirst("Task-target")):
            return
        self.check_tasks_alignment(
            self.textgrid.getFirst("Task-merged"),
            ["Patient-merged", "Sentence-merged", "Non-patient-merged"])
        self.check_tasks_alignment(
            self.textgrid.getFirst("Task-target"),
            ["Patient-target", "Sentence-target", "Non-patient-target"])
        self.check_sentence_tier(
            self.textgrid.getFirst("Sentence-merged"),
            self.textgrid.getFirst("Patient-merged"),
            self.textgrid.getFirst("Task-merged"))
        self.check_sentence_tier(
            self.textgrid.getFirst("Sentence-target"),
            self.textgrid.getFirst("Patient-target"),
            self.textgrid.getFirst("Task-target"))
        self.check_np_tier(self.textgrid.getFirst("Non-patient-merged"))
        self.check_np_tier(self.textgrid.getFirst("Non-patient-target"))
        self.check_tasks_annotations(self.textgrid.getFirst("Task-merged"),
                                     self.textgrid.getFirst("Patient-merged"),
                                     self.textgrid.getFirst("Sentence-merged"))
        self.check_tasks_annotations(self.textgrid.getFirst("Task-target"),
                                     self.textgrid.getFirst("Patient-target"),
                                     self.textgrid.getFirst("Sentence-target"))
        self.check_annotations_matching()
        self.check_times_merging()

    def gen_final_textgrid(self) -> TextGrid:
        pass

