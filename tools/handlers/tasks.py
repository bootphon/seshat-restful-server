from tools.handlers.commons import AnnotatorMethodView, AdminMethodView, LoggedInMethodView
from flask_rest_api import Blueprint

from tools.schemas.tasks import TaskShort, TaskAssignment, TaskFullAdmin, TaskComment, TaskCommentSubmission, \
    TaskTextgridSubmission, TextgridErrors

tasks_blp = Blueprint("tasks", __name__, url_prefix="/tasks",
                      description="Operations to manage, interact with and display tasks")


@tasks_blp.route("/list/assigned")
class ListAssignedTasksHandler(AnnotatorMethodView):

    @tasks_blp.response(TaskShort(many=True))
    def get(self):
        pass


@tasks_blp.route("assign")
class AssignTasksHandler(AdminMethodView):

    @tasks_blp.arguments(TaskAssignment(many=True))
    @tasks_blp.response(code=200)
    def post(self):
        pass

#TODO: lock task and delete task handlers

@tasks_blp.route("/status/admin/<task_id>")
class GetAdminTaskDataHandler(AdminMethodView):

    @tasks_blp.response(TaskFullAdmin())
    def get(self, task_id: str):
        pass


@tasks_blp.route("/status/annotator/<task_id>")
class GetAnnotatorTaskDataHandler(AnnotatorMethodView):

    def get(self, task_id: str):
        pass


@tasks_blp.route("/submit/<task_id>")
class SubmitTaskFileHandler(AnnotatorMethodView):

    @tasks_blp.arguments(TaskTextgridSubmission)
    @tasks_blp.response(TextgridErrors)
    def post(self, task_id: str):
        pass


@tasks_blp.route("/check/<task_id>")
class CheckTaskFileHandler(AnnotatorMethodView):

    @tasks_blp.arguments(TaskTextgridSubmission)
    @tasks_blp.response(TextgridErrors)
    def post(self):
        pass


@tasks_blp.route("/comment/<task_id>")
class TaskCommentHandler(LoggedInMethodView):

    @tasks_blp.response(TaskComment(many=True))
    def get(self, task_id: str):
        pass

    @tasks_blp.arguments(TaskCommentSubmission)
    @tasks_blp.response(code=200)
    def post(self, task_id: str):
        pass
