from tools.handlers.commons import AdminMethodView
from .commons import LoggedInMethodView
from flask_rest_api import Blueprint


users_blp = Blueprint("users", __name__, url_prefix="users/",
                      description="Users administration and creation")


class CreateAnnotatorHandler(AdminMethodView):
    pass


class EditAnnotatorHandler(AdminMethodView):
    pass


class DeleteAnnotatorHandler(AdminMethodView):
    pass


class LockAnnotatorHandler(AdminMethodView):
    pass


class ListAnnotatorsHandler(AdminMethodView):
    pass