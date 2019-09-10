from tools.handlers.commons import AnnotatorMethodView, AdminMethodView
from flask_rest_api import Blueprint

tasks_blp = Blueprint("tasks", __name__, url_prefix="tasks/",
                      description="Operations to manage, interact with and display tasks")


@tasks_blp.route("list/assigned")
class ListAssignedTasksHandler(AnnotatorMethodView):
    pass


@tasks_blp.route("list/annotator")
class ListAnnotatorTasksHandler(AdminMethodView):
    pass


@tasks_blp.route("assign")
class AssignTasksHandler(AdminMethodView):
    pass


@tasks_blp.route("status/admin")
class GetAdminTaskStatusHandler(AdminMethodView):
    pass


@tasks_blp.route("status/annotator")
class GetAnnotatorTaskStatusHandler(AnnotatorMethodView):
    pass


@tasks_blp.route("submit")
class SubmitTaskFileHandler(AnnotatorMethodView):
    pass


@tasks_blp.route("check")
class CheckTaskFileHandler(AnnotatorMethodView):
    pass