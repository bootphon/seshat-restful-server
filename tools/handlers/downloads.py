from .commons import LoggedInMethodView
from flask import Blueprint

downloads_blp = Blueprint("downloads", __name__, url_prefix="/downloads")


@downloads_blp.route("/task/<task_id>/starter")
class TaskStarterArchiveDownload(LoggedInMethodView):

    def get(self, task_id: str):
        pass


@downloads_blp.route("/task/<task_id>/current_textgrid")
class CurrentTextGridDownloadHandler(LoggedInMethodView):

    def get(self, task_id: str):
        pass


@downloads_blp.route("/task/<task_id>/<file>")
class TaskFileDownload(LoggedInMethodView):

    def get(self, task_id: str, file: str):
        pass