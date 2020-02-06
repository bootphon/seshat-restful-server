import io
import zipfile
from io import BytesIO
from pathlib import Path
from typing import List

from flask import send_file, abort
from flask_smorest import Blueprint

from .commons import AdminMethodView, AnnotatorMethodView
from ..schemas.tasks import TaskTextGridList
from .commons import LoggedInMethodView
from ..models import BaseTask, Campaign, Annotator, BaseTextGridDocument

downloads_blp = Blueprint("downloads", __name__, url_prefix="/downloads")


@downloads_blp.route("task/<task_id>/starter")
class TaskStarterArchiveDownload(LoggedInMethodView):

    def get(self, task_id: str):
        """Download a task's starter zip (containing the auto-generated template
        textgrid as well as well as some optional audio file)"""
        task: BaseTask = BaseTask.objects.get(id=task_id)
        if isinstance(self.user, Annotator):
            task.log_download(self.user, "starter_zip")
        return send_file(io.BytesIO(task.get_starter_zip()),
                         attachment_filename=task.name + ".zip",
                         cache_timeout=0)


@downloads_blp.route("task/<task_id>/current_textgrid")
class CurrentTextGridDownloadHandler(AnnotatorMethodView):

    def get(self, task_id: str):
        """Download the task's current textgrid file that is to be annotated"""
        task: BaseTask = BaseTask.objects.get(id=task_id)
        tg_name = task.current_tg_template(self.user)
        task.log_download(self.user, tg_name)
        tg_doc = task.textgrids[tg_name]
        return send_file(tg_doc.textgrid_file,
                         as_attachment=True,
                         attachment_filename="%s_%s.TextGrid"
                                             % (task.name, tg_name),
                         cache_timeout=0)


@downloads_blp.route("task/<task_id>/conflict_log")
class ConflictLogDownloadHandler(AnnotatorMethodView):

    def get(self, task_id: str):
        """Download the task's conflict log (in case the task is a double-annotator one)"""
        task: BaseTask = BaseTask.objects.get(id=task_id)
        tg_name = task.current_tg_template(self.user)
        task.log_download(self.user, tg_name)
        tg_doc = task.textgrids[tg_name]
        return send_file(tg_doc.textgrid_file,
                         as_attachment=True,
                         attachment_filename="%s_%s.TextGrid"
                                             % (task.name, tg_name),
                         cache_timeout=0)


@downloads_blp.route("task/<task_id>/textgrids")
class TaskTextGridListDownload(AdminMethodView):

    @staticmethod
    def retrieve_file(task: BaseTask, file_name: str):
        try:
            if isinstance(task.files[file_name], BaseTextGridDocument):
                data = task.files[file_name].textgrid_file.read()
                filename = f"{task.name}_{file_name}.TextGrid"
            else:
                return abort(404, message="Textgrid hasn't been completed yet")
        except KeyError:
            return abort(404)

        return data, filename

    @downloads_blp.arguments(TaskTextGridList, as_kwargs=True)
    def get(self, task_id: str, names: List[str]):
        task: BaseTask = BaseTask.objects.get(id=task_id)
        if len(names) == 1:
            data, filename = self.retrieve_file(task, names[0])
        else:  # build a zip
            buffer = BytesIO()
            arch_name = task.data_file + task.TASK_TYPE.replace(" ", "_")
            with zipfile.ZipFile(buffer, "w", zipfile.ZIP_STORED) as zfile:
                zip_folder: Path = Path(arch_name)
                for tg_name in names:
                    tg_archpath = zip_folder / Path(tg_name + ".TextGrid")
                    tg_doc = task.textgrids[tg_name]
                    if tg_doc is not None:
                        zfile.writestr(str(tg_archpath), tg_doc.to_str())

            data = buffer.getvalue()
            filename = arch_name + ".zip"

        return send_file(io.BytesIO(data),
                         as_attachment=True,
                         attachment_filename=filename,
                         cache_timeout=0)


@downloads_blp.route("textgrid/<textgrid_id>")
class TextGridDownloadHandler(AdminMethodView):

    def get(self, textgrid_id):
        """Download a specific textgrid"""
        tg_doc: BaseTextGridDocument = BaseTextGridDocument.objects.get(id=textgrid_id)
        # TODO : figure out textgrid name based on task/annotators/campaign
        return send_file(tg_doc.textgrid_file,
                         as_attachment=True,
                         attachment_filename="%s.TextGrid" % textgrid_id,
                         cache_timeout=0)


@downloads_blp.route("campaign/archive/<campaign_slug>")
class FullAnnotArchiveDownload(AdminMethodView):

    def get(self, campaign_slug: str):
        """Download a campaign's full annotation archive"""
        campaign: Campaign = Campaign.objects.get(slug=campaign_slug)

        return send_file(io.BytesIO(campaign.get_full_annots_archive()),
                         attachment_filename=campaign.slug + ".zip",
                         as_attachment=True,
                         cache_timeout=0)

