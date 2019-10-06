from pathlib import Path
from typing import Dict

from flask_rest_api import Blueprint, abort
from flask import current_app
from .commons import AnnotatorMethodView, AdminMethodView, LoggedInMethodView
from ..models import SingleAnnotatorTask, DoubleAnnotatorTask, Annotator, Campaign, BaseTask
from ..models.errors import error_log
from ..schemas.tasks import TaskShort, TaskAssignment, TaskFullAdmin, \
    TaskComment, TaskCommentSubmission, \
    TaskTextgridSubmission, TextgridErrors, TaskLockRequest

tasks_blp = Blueprint("tasks", __name__, url_prefix="/tasks",
                      description="Operations to manage, interact with and display tasks")


@tasks_blp.route("/list/assigned")
class ListAssignedTasksHandler(AnnotatorMethodView):

    @tasks_blp.response(TaskShort(many=True))
    def get(self):
        """Lists all tasks assigned to the currently logged-in annotator"""
        return [task.short_status for task in self.user.assigned_tasks]


@tasks_blp.route("assign")
class AssignTasksHandler(AdminMethodView):

    @tasks_blp.arguments(TaskAssignment(many=True))
    @tasks_blp.response(code=200)
    def post(self, args: Dict):
        campaign = Campaign.objects(slug=args["campaign"])
        if args.get("single_annot_assign") is not None:
            annotator = Annotator.objects(username=args["single_annot_assign"]["annotator"])
            task_class = SingleAnnotatorTask
            annotators = {"annotator" : annotator}
        else:
            reference = Annotator.objects(username=args["double_annot_assign"]["reference"])
            target = Annotator.objects(username=args["double_annot_assign"]["target"])
            task_class = DoubleAnnotatorTask
            annotators = {"reference": reference,
                          "target": target}

        for file in args["audio_files"]:
            new_task = task_class(**annotators)

            actual_filepath = (Path(current_app.config["CAMPAIGNS_FILES_ROOT"]) / Path(audio_file))
            # TODO : use the campaign to retrieve the file duration
            # TODO : use the campaign's textgrid checker to figure out which tiers to use
            # TODO : generate the template, don't forget to save it
            new_task.campaign = campaign
            new_task.deadline = args["deadline"]
            new_task.save()
            campaign.tasks.append(new_task)
            for user in annotators.values():
                user.assigned_tasks.append(new_task)
        abort(400)
        task_class.notify_assign(list(annotators.values()), campaign)
        campaign.save()
        for user in annotators.values():
            user.save()


@tasks_blp.route("delete/<task_id>")
class DeleteTaskHandler(AdminMethodView):

    @tasks_blp.response(code=200)
    def delete(self, task_id: str):
        task: BaseTask = BaseTask.objects(task_id=task_id)
        task.delete()


@tasks_blp.route("lock/")
class LockTaskHandler(AdminMethodView):

    @tasks_blp.arguments(TaskLockRequest, as_kwargs=True)
    @tasks_blp.response(code=200)
    def post(self, task_id: str, lock_status: bool):
        task: BaseTask = BaseTask.objects(task_id=task_id)
        task.is_locked = lock_status
        task.save()


@tasks_blp.route("/status/admin/<task_id>")
class GetAdminTaskDataHandler(AdminMethodView):

    @tasks_blp.response(TaskFullAdmin)
    def get(self, task_id: str):
        task: BaseTask = BaseTask.objects(task_id=task_id)
        return task.admin_status


@tasks_blp.route("/status/annotator/<task_id>")
class GetAnnotatorTaskDataHandler(AnnotatorMethodView):

    def get(self, task_id: str):
        task: BaseTask = BaseTask.objects(task_id=task_id)
        return task.annotator_status


@tasks_blp.route("/submit/<task_id>")
class SubmitTaskFileHandler(AnnotatorMethodView):

    @tasks_blp.arguments(TaskTextgridSubmission)
    @tasks_blp.response(TextgridErrors)
    def post(self, args, task_id: str):
        task: BaseTask = BaseTask.objects(task_id=task_id)
        error_log.flush()
        task.submit_textgrid(args["textgrid_str"], self.user)
        return error_log.to_errors_summary()


@tasks_blp.route("/validate/<task_id>")
class ValidateTaskFileHandler(AnnotatorMethodView):

    @tasks_blp.arguments(TaskTextgridSubmission)
    @tasks_blp.response(TextgridErrors)
    def post(self, task_id: str, args):
        task: BaseTask = BaseTask.objects(task_id=task_id)
        error_log.flush()
        task.validate_textgrid(args["textgrid_str"], self.user)
        return error_log.to_errors_summary()


@tasks_blp.route("/comment/<task_id>")
class TaskCommentHandler(LoggedInMethodView):

    @tasks_blp.response(TaskComment(many=True))
    def get(self, task_id: str):
        task: BaseTask = BaseTask.objects(task_id=task_id)
        return [comment.msg_form for comment in task]

    @tasks_blp.arguments(TaskCommentSubmission, as_kwargs=True)
    @tasks_blp.response(code=200)
    def post(self, content, task_id: str):
        task: BaseTask = BaseTask.objects(task_id=task_id)
        task.add_comment(content, self.user)
