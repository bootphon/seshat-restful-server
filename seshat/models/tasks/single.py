from datetime import datetime
from enum import Enum
from typing import Dict, Optional

from mongoengine import ReferenceField, signals

from ..textgrids import BaseTextGridDocument, SingleAnnotatorTextGrid
from ..errors import error_log
from .base import BaseTask


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

    def allow_file_upload(self, annotator: 'Annotator') -> bool:
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

        tg = SingleAnnotatorTextGrid.from_textgrid(textgrid, self.annotators, self)
        tg.check()
        if not error_log.has_errors:
            self.is_done = True
            if self.final_tg is None:
                self.notify_done()
                self.campaign.update_stats()
            self.final_tg = tg
            self.finish_time = datetime.now()

        self.cascade_save()
        self._log_upload(textgrid, annotator, not error_log.has_errors)

    def validate_textgrid(self, textgrid: str, annotator: 'Annotator'):
        if self.is_locked:
            return

        error_log.flush()
        tg = SingleAnnotatorTextGrid.from_textgrid(textgrid, [self.annotator], self)

        tg.check()
        self._log_upload(textgrid, annotator, not error_log.has_errors)

signals.post_delete.connect(BaseTask.post_delete_cleanup, sender=SingleAnnotatorTask)
signals.pre_save.connect(BaseTask.pre_save, sender=SingleAnnotatorTask)
