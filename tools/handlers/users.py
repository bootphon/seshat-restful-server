from tools.handlers.commons import AdminMethodView
from .commons import LoggedInMethodView
from flask_rest_api import Blueprint


users_blp = Blueprint("users", __name__, url_prefix="/users",
                      description="Users administration and creation")


@users_blp.route("/manage")
class ManageAnnotatorHandler(AdminMethodView):

    def post(self):
        """Adds a new user"""
        pass

    def delete(self):
        """Deletes an existing user"""
        pass

    def put(self):
        """Updates an existing user"""
        pass


@users_blp.route("/lock")
class LockAnnotatorHandler(AdminMethodView):

    def post(self):
        pass


@users_blp.route("/list")
class ListAnnotatorsHandler(AdminMethodView):

    def get(self):
        pass