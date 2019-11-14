from flask.views import MethodView
from flask_smorest import Blueprint, abort
from marshmallow import Schema, fields
from mongoengine import Q
from seshat.models import Annotator

from seshat.schemas.users import UserShortProfile, NotificationsCount
from ..models import User
from ..schemas.users import LoginCredentials, ConnectionToken, \
    NotificationData, NotificationDelete

from .commons import LoggedInMethodView
from ..models.users import Notification

accounts_blp = Blueprint("accounts", __name__, url_prefix="/accounts",
                         description="Login/logout operations")


class HttpErrorCode(Schema):
    code = fields.Int(required=True)
    message = fields.Str(required=True)


@accounts_blp.route("/login")
class LoginHandler(MethodView):

    @accounts_blp.arguments(LoginCredentials)
    @accounts_blp.response(ConnectionToken)
    def post(self, args):
        """Log in to the account. Returns the connection token"""
        user = User.objects(Q(username=args["login"]) | Q(email=args["login"])).first()
        if user is None:
            return abort(401, message="Invalid login or password")

        if isinstance(user, Annotator):
            if user.locked:
                return abort(401, "You cannot login because your account has been locked.")

        if user.check_password(args["password"]):
            return {"token": user.get_token()}
        else:
            return abort(401, mesage="Invalid login or password")


@accounts_blp.route("/data")
class UserDataHandler(LoggedInMethodView):

    @accounts_blp.response(UserShortProfile)
    def get(self):
        return self.user.short_profile


@accounts_blp.route("/logout")
class LogoutHandler(LoggedInMethodView):

    @accounts_blp.response(code=200)
    def post(self):
        """Log out form the server. Flushes the annotator's cookie"""
        self.user.delete_token()


@accounts_blp.route("/notifications")
class NotificationsHandler(LoggedInMethodView):

    @accounts_blp.response(NotificationData(many=True))
    def get(self):
        """Retrieve the user's notifications"""
        return [notif.to_msg() for notif in self.user.pending_notifications]

    @accounts_blp.arguments(NotificationDelete)
    @accounts_blp.response(code=200)
    def delete(self, args):
        """Delete a user's notification"""
        notif: Notification = Notification.objects.get(id=args["notif_id"])
        if not notif in self.user.pending_notifications:
            return abort(501, message="Unable to delete notification because it's not yours!")
        notif.delete()


@accounts_blp.route("/notifications/count")
class NotificationsCountHandler(LoggedInMethodView):

    @accounts_blp.response(NotificationsCount)
    def get(self):
        return {'count': len(self.user.pending_notifications)}
