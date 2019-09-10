from flask.views import MethodView
from .commons import LoggedInMethodView
from flask_rest_api import Blueprint

accounts_blp = Blueprint("accounts", __name__, url_prefix="accounts/",
                         description="Login/logout operations")


class LoginHandler(MethodView):
    pass


class LogoutHandler(LoggedInMethodView):
    pass