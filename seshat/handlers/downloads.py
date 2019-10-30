import io
from typing import List

from flask_smorest import Blueprint, abort
from flask import send_file

from seshat.schemas.tasks import TaskTextGridList
from ..models import BaseTask, Campaign, Annotator, BaseTextGridDocument

from seshat.handlers.commons import AdminMethodView, AnnotatorMethodView
from .commons import LoggedInMethodView

downloads_blp = Blueprint("downloads", __name__, url_prefix="/downloads")


@downloads_blp.route("task/<task_id>/starter")
class TaskStarterArchiveDownload(LoggedInMethodView):

    def get(self, task_id: str):
        task: BaseTask = BaseTask.objects.get(id=task_id)
        if isinstance(self.user, Annotator):
            task.log_download(self.user, "starter_zip")
        return send_file(io.BytesIO(task.get_starter_zip()),
                         attachment_filename=task.name + ".zip",
                         cache_timeout=0)


@downloads_blp.route("task/<task_id>/current_textgrid")
class CurrentTextGridDownloadHandler(AnnotatorMethodView):

    def get(self, task_id: str):
        task: BaseTask = BaseTask.objects.get(id=task_id)
        tg_name = task.current_tg_template(self.user)
        task.log_download(self.user, tg_name)
        tg_str: str = task.textgrids[tg_name].textgrid.to_str()
        return send_file(io.BytesIO(tg_str.encode()),
                         as_attachment=True,
                         attachment_filename="%s_%s.TextGrid"
                                             % (task.name, tg_name),
                         cache_timeout=0)


@downloads_blp.route("task/<task_id>/conflict_log")
class ConflictLogDownloadHandler(AnnotatorMethodView):

    def get(self, task_id: str):
        task: BaseTask = BaseTask.objects.get(id=task_id)
        tg_name = task.current_tg_template(self.user)
        task.log_download(self.user, tg_name)
        tg_str: str = task.textgrids[tg_name].textgrid.to_str()
        return send_file(io.BytesIO(tg_str.encode()),
                         as_attachment=True,
                         attachment_filename="%s_%s.TextGrid"
                                             % (task.name, tg_name),
                         cache_timeout=0)


@downloads_blp.route("task/<task_id>")
class TaskFileDownload(LoggedInMethodView):

    @staticmethod
    def retrieve_file(task: BaseTask, file_name: str):
        if isinstance(task.files[file_name], BaseTextGridDocument):
            data = task.files[file_name].textgrid_file.read()
            filename = "%s_%s.TextGrid" % (task.name, file_name)
        elif file_name == "conflicts_log":
            data = task.files[file_name].encode("utf-8")
            filename = "%s_%s.Conflicts" % (task.name, file_name)
        else:
            return abort(404)
        return data, filename

    @downloads_blp.arguments(TaskTextGridList, as_kwargs=True)
    def get(self, task_id: str, names: List[str]):
        task: BaseTask = BaseTask.objects.get(id=task_id)
        if isinstance(self.user, Annotator):
            task.log_download(self.user, file_name)

        if len(names) == 1:
            data, filename = self.retrieve_file(task, names[0])
        else:  # build a zip
            pass

        return send_file(io.BytesIO(data),
                         as_attachment=True,
                         attachment_filename=filename,
                         cache_timeout=0)


@downloads_blp.route("textgrid/<textgrid_id>")
class TextGridDownloadHandler(AdminMethodView):

    def get(self, textgrid_id):
        return


@downloads_blp.route("campaign/<campaign_slug>")
class FullAnnotArchiveDownload(AdminMethodView):

    def get(self, campaign_slug: str):
        campaign: Campaign = Campaign.objects.get(slug=campaign_slug)

        return send_file(io.BytesIO(campaign.get_full_annots_archive()),
                         attachment_filename=campaign.slug + ".zip",
                         cache_timeout=0)