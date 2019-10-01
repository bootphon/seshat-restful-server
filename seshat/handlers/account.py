from flask.views import MethodView
from flask_rest_api import Blueprint
from mongoengine import Q
from tools.models import User
from tools.schemas.users import LoginCredentials, ConnectionToken, \
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
        user = User.objects(Q(username=args["login"]) | Q(email=args["login"])).first()
        if user is None:
            return  # returns a 401 error

        if user.check_password(args["password"]):
            return {"token": user.get_token()}
        else:
            return  # returns a 401 error


@accounts_blp.route("/logout")
class LogoutHandler(LoggedInMethodView):

    @accounts_blp.response(code=200)
    def post(self):
        self.user.delete_token()


@accounts_blp.route("/notifications")
class NotificationsHandler(LoggedInMethodView):

    @accounts_blp.response(NotificationData(many=True))
    def get(self):
        return [notif.to_msg() for notif in self.user.pending_notifications]

    @accounts_blp.arguments(NotificationDelete)
    @accounts_blp.response(code=200)
    def delete(self, args):
        notif: Notification = Notification.objects. \
            get(id=args["notif_id"])
        notif.delete()
