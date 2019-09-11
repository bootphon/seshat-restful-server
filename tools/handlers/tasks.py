from tools.handlers.commons import AnnotatorMethodView, AdminMethodView
from flask_rest_api import Blueprint

tasks_blp = Blueprint("tasks", __name__, url_prefix="/tasks",
                      description="Operations to manage, interact with and display tasks")


@tasks_blp.route("/list/assigned")
class ListAssignedTasksHandler(AnnotatorMethodView):

    def get(self):
        pass


@tasks_blp.route("/list/annotator/<username>")
class ListAnnotatorTasksHandler(AdminMethodView):

    def get(self, username: str):
        pass


@tasks_blp.route("assign")
class AssignTasksHandler(AdminMethodView):

    def post(self):
        pass


@tasks_blp.route("/status/admin/<task_id>")
class GetAdminTaskStatusHandler(AdminMethodView):

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

