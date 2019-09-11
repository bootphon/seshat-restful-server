from marshmallow import Schema, fields
from ..models import Annotator
from .tasks import TaskShort


class LoginCredentials(Schema):
    pass


class ConnectionCredentials(Schema):
    pass


class AnnotatorCreation(Schema):
    pass


class AnnotatorDeletion(Schema):
    pass


class AnnotatorShortProfile(Schema):
    pass


class AnnotatorFullProfile(AnnotatorShortProfile):

    tasks = fields.List(fields.Nested(TaskShort))
