from typing import Dict

from flask_rest_api import Blueprint, abort
from mongoengine import NotUniqueError, DoesNotExist, ValidationError

from ..handlers.commons import AdminMethodView
from ..schemas.users import AnnotatorCreation, AnnotatorFullProfile, AnnotatorShortProfile, AnnotatorDeletion, \
    AnnotatorLockRequest
from ..models import Annotator

users_blp = Blueprint("users", __name__, url_prefix="/users",
                      description="Users administration and creation")


@users_blp.route("/manage")
class ManageAnnotatorHandler(AdminMethodView):

    @users_blp.arguments(AnnotatorCreation)
    @users_blp.response(code=200)
    def post(self, args):
        """Adds a new user"""
        if len(args["password"])  < 8 :
            abort(403, message="Password has to be longer")

        try:
            new_user = Annotator(**args)
            password, salt = Annotator.create_password_hash(args["password"])
            new_user.password = password
            new_user.salt = salt
            new_user.save()
        except NotUniqueError:
            abort(403, message="Username or email already present in database")

    @users_blp.arguments(AnnotatorDeletion, as_kwargs=True)
    @users_blp.response(code=200)
    def delete(self, username: str):
        """Deletes an existing user"""
        try:
            user: Annotator = Annotator.objects(username=username)
            user.delete()
        except DoesNotExist:
            abort(404, message="User not found in database")

    @users_blp.arguments(AnnotatorCreation)
    @users_blp.response(code=200)
    def put(self, args: Dict):
        """Updates an existing user"""
        try:
            user: Annotator = Annotator.objects(args["username"])
            del args["username"]
            user.update(**args)
        except NotUniqueError:
            abort(403, message="Email already in database")
        except ValidationError:
            abort(403, message="Invalid data")


@users_blp.route("/view/<username>")
class AnnotatorFullProfileHandler(AdminMethodView):

    @users_blp.response(AnnotatorFullProfile)
    def get(self, username: str):
        """Display a an annotator's full profile"""
        user: Annotator = Annotator.objects(username=username)
        return user.full_profile


@users_blp.route("/lock")
class LockAnnotatorHandler(AdminMethodView):

    @users_blp.arguments(AnnotatorLockRequest, as_kwargs=True)
    @users_blp.response(code=200)
    def post(self, username: str, lock_status: bool):
        """Locks or unlocks an annotator's account"""
        user: Annotator = Annotator.objects(username=username)
        user.locked = lock_status
        user.save()


@users_blp.route("/list")
class ListAnnotatorsHandler(AdminMethodView):

    @users_blp.response(AnnotatorShortProfile(many=True))
    def get(self):
        """Lists all annotators registered in DB"""
        return [user.short_profile for user in Annotator.objects]
