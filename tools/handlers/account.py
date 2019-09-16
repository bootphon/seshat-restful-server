from flask.views import MethodView

from tools.schemas.users import LoginCredentials, ConnectionCredentials, Notification, NotificationDelete
from .commons import LoggedInMethodView
from flask_rest_api import Blueprint

accounts_blp = Blueprint("accounts", __name__, url_prefix="/accounts",
                         description="Login/logout operations")


@accounts_blp.route("/login")
class LoginHandler(MethodView):

    @accounts_blp.arguments(LoginCredentials)
    @accounts_blp.response(ConnectionCredentials)
    def post(self, args):
        pass


@accounts_blp.route("/logout")
class LogoutHandler(LoggedInMethodView):

    @accounts_blp.response(code=200)
    def get(self):
        pass


@accounts_blp.route("/notifications")
class NotificationsHandler(LoggedInMethodView):

    @accounts_blp.response(Notification(many=True))
    def get(self):
        pass

    @accounts_blp.arguments(NotificationDelete)
    @accounts_blp.response(code=200)
    def delete(self, args):
        pass