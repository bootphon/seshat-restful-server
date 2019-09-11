from tools.handlers.commons import AnnotatorMethodView, AdminMethodView
from flask_rest_api import Blueprint

from tools.schemas.tasks import TaskShort, TaskAssignment, TaskFullAdmin

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


@tasks_blp.route("/status/admin/<task_id>")
class GetAdminTaskStatusHandler(AdminMethodView):

    @tasks_blp.response(TaskFullAdmin())
    def get(self, task_id: str):
        pass


@tasks_blp.route("/status/annotator/<task_id>")
class GetAnnotatorTaskStatusHandler(AnnotatorMethodView):

    def get(self, task_id: str):
        pass


@tasks_blp.route("/submit")
class SubmitTaskFileHandler(AnnotatorMethodView):

    def post(self):
        pass


@tasks_blp.route("check")
class CheckTaskFileHandler(AnnotatorMethodView):

    def post(self):
        pass

