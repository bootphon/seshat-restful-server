from flask.views import MethodView
from .commons import LoggedInMethodView
from flask_rest_api import Blueprint

accounts_blp = Blueprint("accounts", __name__, url_prefix="/accounts",
                         description="Login/logout operations")


@accounts_blp.route("/login")
class LoginHandler(MethodView):

    def post(self):
        pass


@accounts_blp.route("/logout")
class LogoutHandler(LoggedInMethodView):

    def get(self):
        pass