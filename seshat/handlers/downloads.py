import io

from flask import Blueprint, send_file
from tools.models import BaseTask
from tools.models.users import Annotator

from .commons import LoggedInMethodView

downloads_blp = Blueprint("downloads", __name__, url_prefix="/downloads")


@downloads_blp.route("/task/<task_id>/starter")
class TaskStarterArchiveDownload(LoggedInMethodView):

    def get(self, task_id: str):
        task: BaseTask = BaseTask.objects.get(id=task_id)
        if isinstance(self.user, Annotator):
            task.log_download(self.user, "starter_zip")
        return send_file(io.BytesIO(task.get_starter_zip()),
                         attachment_filename=task.name + ".zip",
                         cache_timeout=0)


@downloads_blp.route("/task/<task_id>/current_textgrid")
class CurrentTextGridDownloadHandler(LoggedInMethodView):

    def get(self, task_id: str):
        task: BaseTask = BaseTask.objects.get(id=task_id)
        tg_name = task.current_tg_template
        if isinstance(self.user, Annotator):
            task.log_download(self.user, tg_name)
        tg_str: str = task.textgrids[tg_name].textgrid_str
        return send_file(io.BytesIO(tg_str.encode()),
                         as_attachment=True,
                         attachment_filename="%s_%s.TextGrid"
                                             % (task.name, tg_name),
                         cache_timeout=0)


@downloads_blp.route("/task/<task_id>/<file_name>")
class TaskFileDownload(LoggedInMethodView):

    def get(self, task_id: str, file_name: str):
        task: BaseTask = BaseTask.objects.get(id=task_id)
        if isinstance(self.user, Annotator):
            task.log_download(self.user, file_name)
        tg_str: str = task.textgrids[file_name].textgrid_str
        return send_file(io.BytesIO(tg_str.encode()),
                         as_attachment=True,
                         attachment_filename="%s_%s.TextGrid"
                                             % (task.name, file_name),
                         cache_timeout=0)
