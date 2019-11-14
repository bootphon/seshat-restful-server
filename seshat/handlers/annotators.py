from typing import Dict

from flask_smorest import Blueprint, abort
from mongoengine import NotUniqueError, DoesNotExist, ValidationError

from seshat.schemas.tasks import TaskShortStatus
from seshat.schemas.users import AnnotatorEdition, AnnotatorPasswordChange
from ..handlers.commons import AdminMethodView
from ..schemas.users import AnnotatorCreation, AnnotatorProfile, AnnotatorDeletion, \
    AnnotatorLockRequest
from ..models import Annotator

annotators_blp = Blueprint("annotators", __name__, url_prefix="/annotators",
                           description="Annotators administration and creation")


@annotators_blp.route("/manage")
class ManageAnnotatorHandler(AdminMethodView):

    @annotators_blp.arguments(AnnotatorCreation)
    @annotators_blp.response(code=200)
    def post(self, args):
        """Adds a new user"""
        if len(args["password"]) < 8:
            abort(403, message="Password has to be longer")

        try:
            password = args.pop("password")
            new_user = Annotator(**args)
            pass_hash, salt = Annotator.create_password_hash(password)
            new_user.salted_password_hash = pass_hash
            new_user.salt = salt
            new_user.save()
        except NotUniqueError:
            abort(403, message="Username or email already present in database")

    @annotators_blp.arguments(AnnotatorDeletion, as_kwargs=True)
    @annotators_blp.response(code=200)
    def delete(self, username: str):
        """Deletes an existing user"""
        try:
            user: Annotator = Annotator.objects.get(username=username)
            user.delete()
        except DoesNotExist:
            abort(404, message="User not found in database")

    @annotators_blp.arguments(AnnotatorEdition)
    @annotators_blp.response(code=200)
    def put(self, args: Dict):
        """Updates an existing user"""
        try:
            user: Annotator = Annotator.objects.get(args["username"])
            del args["username"]
            user.update(**args)
            user.save()
        except NotUniqueError:
            abort(403, message="Email already in database")
        except ValidationError:
            abort(403, message="Invalid data")


@annotators_blp.route("password/change")
class AnnotatorChangePasswordHandler(AdminMethodView):

    @annotators_blp.arguments(AnnotatorPasswordChange, as_kwargs=True)
    def post(self, username: str, password: str):
        if len(password) < 8:
            abort(403, message="Password has to be longer")
        annotator: Annotator = Annotator.objects.get(username)
        pass_hash, salt = Annotator.create_password_hash(password)
        annotator.salted_password_hash = pass_hash
        annotator.salt = salt
        annotator.save()


@annotators_blp.route("/view/<username>")
class AnnotatorFullProfileHandler(AdminMethodView):

    @annotators_blp.response(AnnotatorProfile)
    def get(self, username: str):
        """Display a an annotator's full profile"""
        annotator: Annotator = Annotator.objects.get(username=username)
        return annotator.profile


@annotators_blp.route("/list/tasks/<username>")
class AnnotatorTasksHandler(AdminMethodView):

    @annotators_blp.response(TaskShortStatus(many=True))
    def get(self, username: str):
        annotator: Annotator = Annotator.objects.get(username=username)
        return [task.short_status for task in annotator.assigned_tasks]


@annotators_blp.route("/lock")
class LockAnnotatorHandler(AdminMethodView):

    @annotators_blp.arguments(AnnotatorLockRequest, as_kwargs=True)
    @annotators_blp.response(code=200)
    def post(self, username: str, lock_status: bool):
        """Locks or unlocks an annotator's account"""
        user: Annotator = Annotator.objects.get(username=username)
        user.locked = lock_status
        user.save()


@annotators_blp.route("/list")
class ListAnnotatorsHandler(AdminMethodView):

    @annotators_blp.response(AnnotatorProfile(many=True))
    def get(self):
        """Lists all annotators registered in DB"""
        return [user.profile for user in Annotator.objects]
