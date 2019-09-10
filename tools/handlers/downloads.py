from .commons import LoggedInMethodView
from flask import Blueprint

downloads_blp = Blueprint("downloads", __name__, url_prefix="downloads/")


class TaskStarterArchiveDownload(LoggedInMethodView):
    pass


class CurrentTextGridDownloadHandler(LoggedInMethodView):
    pass


class TaskFileDownload(LoggedInMethodView):

    def get(self):
        pass