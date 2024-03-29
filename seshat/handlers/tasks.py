from typing import Dict, List

from flask_smorest import Blueprint, abort

from seshat.schemas.tasks import TaskFullStatusAnnotator, TaskIdsList
from .commons import AnnotatorMethodView, AdminMethodView, LoggedInMethodView
from ..models import SingleAnnotatorTask, DoubleAnnotatorTask, Annotator, Campaign, BaseTask
from ..models.errors import error_log
from ..schemas.tasks import TaskShortStatus, TasksAssignment, TaskFullStatusAdmin, \
    TaskComment, TaskCommentSubmission, \
    TaskTextgridSubmission, TextGridErrors, TaskLockRequest

tasks_blp = Blueprint("tasks", __name__, url_prefix="/tasks",
                      description="Operations to manage, interact with and display tasks")


@tasks_blp.route("/list/assigned")
class ListAssignedTasksHandler(AnnotatorMethodView):

    @tasks_blp.response(200, schema=TaskShortStatus(many=True))
    def get(self):
        """Lists all tasks assigned to the currently logged-in annotator"""
        return [task.short_status for task in self.user.assigned_tasks]


@tasks_blp.route("assign")
class AssignTasksHandler(AdminMethodView):

    @tasks_blp.arguments(TasksAssignment)
    @tasks_blp.response(200)
    def post(self, args: Dict):
        """Assign annotating tasks (linked to an audio file) to annotators"""
        campaign = Campaign.objects.get(slug=args["campaign"])
        if args.get("single_annot_assign") is not None:
            annotator = Annotator.objects.get(username=args["single_annot_assign"]["annotator"])
            task_class = SingleAnnotatorTask
            annotators = {"annotator": annotator}
        else:
            reference = Annotator.objects.get(username=args["double_annot_assign"]["reference"])
            target = Annotator.objects.get(username=args["double_annot_assign"]["target"])
            task_class = DoubleAnnotatorTask
            annotators = {"reference": reference,
                          "target": target}

        for file in args["audio_files"]:
            new_task: BaseTask = task_class(**annotators)
            template_doc = campaign.gen_template_tg(file)
            template_doc.creators = [self.user]
            template_doc.save()
            new_task.template_tg = template_doc
            new_task.campaign = campaign
            new_task.data_file = file
            new_task.assigner = self.user
            new_task.deadline = args.get("deadline")
            new_task.save()
            template_doc.task = new_task
            template_doc.save()
            campaign.tasks.append(new_task)
            for user in annotators.values():
                user.assigned_tasks.append(new_task)
        task_class.notify_assign(list(annotators.values()), campaign)
        campaign.update_stats()
        campaign.save()
        for user in annotators.values():
            user.save()


@tasks_blp.route("delete/<task_id>")
class DeleteTaskHandler(AdminMethodView):

    @tasks_blp.response(200)
    def delete(self, task_id: str):
        """Delete an assigned task"""
        BaseTask.objects.get(id=task_id).delete()


@tasks_blp.route("delete/list/")
class DeleteTasksListHandler(AdminMethodView):

    @tasks_blp.arguments(TaskIdsList, as_kwargs=True)
    @tasks_blp.response(200)
    def delete(self, task_ids: List[str]):
        """Delete an assigned task"""
        BaseTask.objects(id__in=task_ids).delete()


@tasks_blp.route("delete/<task_id>/textgrid/<tg_name>")
class DeleteTaskTextGridHandler(AdminMethodView):

    @tasks_blp.response(200)
    def delete(self, task_id: str, tg_name: str):
        """Delete an assigned task"""
        task: BaseTask = BaseTask.objects.get(id=task_id)
        task.delete_textgrid(tg_name)


@tasks_blp.route("lock/")
class LockTaskHandler(AdminMethodView):

    @tasks_blp.arguments(TaskLockRequest, as_kwargs=True)
    @tasks_blp.response(200)
    def post(self, task_id: str, lock_status: bool):
        """Lock a task, preventing a user from making any change to it"""
        task: BaseTask = BaseTask.objects.get(id=task_id)
        task.is_locked = lock_status
        task.save()


@tasks_blp.route("/status/admin/<task_id>")
class GetAdminTaskDataHandler(AdminMethodView):

    @tasks_blp.response(200, schema=TaskFullStatusAdmin)
    def get(self, task_id: str):
        """Returns the full task status for the admin task view"""
        task: BaseTask = BaseTask.objects.get(id=task_id)
        return task.admin_status


@tasks_blp.route("/status/annotator/<task_id>")
class GetAnnotatorTaskDataHandler(AnnotatorMethodView):

    @tasks_blp.response(200, schema=TaskFullStatusAnnotator)
    def get(self, task_id: str):
        """Returns the annotator's task status, for the annotator task view"""
        task: BaseTask = BaseTask.objects.get(id=task_id)
        return task.get_annotator_status(self.user)


@tasks_blp.route("/submit/<task_id>")
class SubmitTaskFileHandler(AnnotatorMethodView):

    @tasks_blp.arguments(TaskTextgridSubmission, as_kwargs=True)
    @tasks_blp.response(200, schema=TextGridErrors)
    def post(self, task_id: str, textgrid_str: str):
        """Textgrid submission handler"""
        task: BaseTask = BaseTask.objects.get(id=task_id)
        if task.is_locked:
            return abort(403, message="Task is locked.")
        if not task.allow_file_upload(self.user):
            return abort(403, message="Cannot upload file for this task, at this step.")
        error_log.flush()
        task.submit_textgrid(textgrid_str, self.user)
        if error_log.has_errors:
            return error_log.to_errors_summary()
        else:
            return 200


@tasks_blp.route("/validate/<task_id>")
class ValidateTaskFileHandler(AnnotatorMethodView):

    @tasks_blp.arguments(TaskTextgridSubmission, as_kwargs=True)
    @tasks_blp.response(200, schema=TextGridErrors)
    def post(self, task_id: str, textgrid_str: str):
        """Submits a textgrid to a task. The task will figure out by itself
        the current step it's supposed to belong to, and return any validation error"""
        task: BaseTask = BaseTask.objects.get(id=task_id)
        if task.is_locked:
            return abort(403, message="Task is locked")
        if not task.allow_file_upload(self.user):
            return abort(403, message="Cannot upload file for this task, at this step.")
        error_log.flush()
        task.validate_textgrid(textgrid_str, self.user)
        return error_log.to_errors_summary()


@tasks_blp.route("/comment/<task_id>")
class TaskCommentHandler(LoggedInMethodView):

    @tasks_blp.response(200, schema=TaskComment(many=True))
    def get(self, task_id: str):
        """Retrieves the list of comments for a task"""
        task: BaseTask = BaseTask.objects.get(id=task_id)
        return [comment.to_msg for comment in task.discussion]

    @tasks_blp.arguments(TaskCommentSubmission, as_kwargs=True)
    @tasks_blp.response(200)
    def post(self, content: str, task_id: str):
        """Adds a comment to a task"""
        task: BaseTask = BaseTask.objects.get(id=task_id)
        # If user is administrator, they can still comment even if the task is locked.
        if task.is_locked and isinstance(self.user, Annotator):
            return
        task.add_comment(content, self.user)
        task.notify_comment(self.user)
