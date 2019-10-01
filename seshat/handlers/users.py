from flask_rest_api import Blueprint
from tools.handlers.commons import AdminMethodView
from tools.schemas.users import AnnotatorCreation, AnnotatorFullProfile, AnnotatorShortProfile, AnnotatorDeletion, \
    AnnotatorLockRequest

users_blp = Blueprint("users", __name__, url_prefix="/users",
                      description="Users administration and creation")


@users_blp.route("/manage")
class ManageAnnotatorHandler(AdminMethodView):

    @users_blp.arguments(AnnotatorCreation)
    @users_blp.response(code=200)
    def post(self, args):
        """Adds a new user"""
        pass

    @users_blp.arguments(AnnotatorDeletion)
    def delete(self, args):
        """Deletes an existing user"""
        pass

    @users_blp.arguments(AnnotatorCreation)
    @users_blp.response(code=200)
    def put(self, args):
        """Updates an existing user"""
        pass


@users_blp.route("/view/<username>")
class AnnotatorFullProfileHandler(AdminMethodView):

    @users_blp.response(AnnotatorFullProfile)
    def get(self, username: str):
        """Display a an annotator's full profile"""
        pass


@users_blp.route("/lock")
class LockAnnotatorHandler(AdminMethodView):

    @users_blp.arguments(AnnotatorLockRequest)
    @users_blp.response(code=200)
    def post(self, args):
        pass


@users_blp.route("/list")
class ListAnnotatorsHandler(AdminMethodView):

    @users_blp.response(AnnotatorShortProfile(many=True))
    def get(self):
        pass
