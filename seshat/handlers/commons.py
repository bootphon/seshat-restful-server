import jwt
from flask import request, current_app
from flask.views import MethodView
from flask_smorest import abort
from jwt import DecodeError
from mongoengine import DoesNotExist

from ..models.users import User, Admin, Annotator


class LoggedInMethodView(MethodView):

    def __init__(self):
        self.user: User = None

    def check_user_type(self):
        """Checking that the user has the right type"""
        pass

    def dispatch_request(self, *args, **kwargs):
        token = request.headers["Auth-token"]
        try:
            token_data = jwt.decode(token, current_app.config["SECRET_KEY"],
                                    algorithm="HS256")
        except DecodeError:
            return abort(500, message="Invalid token")

        self.user = User.objects.get(username=token_data["username"])
        self.user.check_token(token)
        self.check_user_type()
        try:
            return super().dispatch_request(*args, **kwargs)
        except DoesNotExist:
            abort(404, message="Entity not found in database")


class AdminMethodView(LoggedInMethodView):

    def __init__(self):
        super().__init__()
        self.user: Admin = None

    def check_user_type(self):
        assert isinstance(self.user, Admin)


class AnnotatorMethodView(LoggedInMethodView):

    def __init__(self):
        super().__init__()
        self.user: Annotator = None

    def check_user_type(self):
        assert isinstance(self.user, Annotator)
        if self.user.locked:
            abort(401, message="You can't login to Seshat because your account has been locked")
