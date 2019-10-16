from flask.views import MethodView
from flask_rest_api import Blueprint
from mongoengine import Q

from seshat.schemas.users import UserShortProfile
from ..models import User
from ..schemas.users import LoginCredentials, ConnectionToken, \
    NotificationData, NotificationDelete

from .commons import LoggedInMethodView
from ..models.users import Notification

accounts_blp = Blueprint("accounts", __name__, url_prefix="/accounts",
                         description="Login/logout operations")


@accounts_blp.route("/login")
class LoginHandler(MethodView):

    @accounts_blp.arguments(LoginCredentials)
    @accounts_blp.response(ConnectionToken, code=401)
    def post(self, args):
        """Log in to the account. Returns the connection token"""
        user = User.objects(Q(username=args["login"]) | Q(email=args["login"])).first()
        if user is None:
            return  # returns a 401 error

        if user.check_password(args["password"]):
            return {"token": user.get_token()}
        else:
            return  # returns a 401 error


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
        notif.delete()
