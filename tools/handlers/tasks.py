from tools.handlers.commons import AnnotatorMethodView, AdminMethodView
from flask_rest_api import Blueprint

tasks_blp = Blueprint("tasks", __name__, url_prefix="tasks/",
                      description="Operations to manage, interact with and display tasks")


class ListAssignedTasksHandler(AnnotatorMethodView):
    pass


class ListAnnotatorTasksHandler(AdminMethodView):
    pass


class AssignTasksHandler(AdminMethodView):
    pass


class GetAdminTaskStatusHandler(AdminMethodView):
    pass


class GetAnnotatorTaskStatusHandler(AnnotatorMethodView):
    pass


class SubmitTaskFileHandler(AnnotatorMethodView):
    pass


class CheckTaskFileHandler(AnnotatorMethodView):
    pass