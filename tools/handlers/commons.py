from flask.views import MethodView
from flask import request
from ..models.users import User, Admin, Annotator


class LoggedInMethodView(MethodView):

    def __init__(self):
        self.user: User = None

    def check_user_type(self):
        """Checking that the user has the right type"""
        pass

    def dispatch_request(self, *args, **kwargs):
        username = request.headers["Auth-username"]
        token = request.headers["Auth-token"]
        self.user = User.objects(username=username)
        self.user.validate_token()
        self.check_user_type()
        return super().dispatch_request(*args, **kwargs)


class AdminMethodView(LoggedInMethodView):

    def check_user_type(self):
        assert isinstance(self.user, Admin)


class AnnotatorMethodView(LoggedInMethodView):

    def check_user_type(self):
        assert isinstance(self.user, Annotator)