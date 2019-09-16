from marshmallow import Schema, fields

from .tasks import TaskShort


class LoginCredentials(Schema):
    username = fields.Str(required=True)
    password = fields.String(required=True)


class ConnectionCredentials(Schema):
    username = fields.Str(required=True)
    token = fields.Str(required=True)


class Notification(Schema):
    time = fields.DateTime(required=True)
    message = fields.Str(required=True)
    object_type = fields.Str(required=True)
    object_id = fields.Str(required=True)
    notif_type = fields.Str(required=True)


class NotificationDelete(Schema):
    notif_id = fields.Str(required=True)


class AnnotatorCreation(Schema):
    firstname = fields.Str(required=True)
    lastname = fields.Str(required=True)
    password = fields.Str(required=True)
    email = fields.Email(required=True)


class AnnotatorDeletion(Schema):
    username = fields.Str(required=True)


class UserShortProfile(Schema):
    fullname = fields.Str(required=True)
    username = fields.Str(required=True)


class AnnotatorShortProfile(UserShortProfile):
    last_activity = fields.DateTime(required=True)
    assigned_tasks = fields.Int(required=True)
    active_tasks = fields.Int(required=True)
    finished_tasks = fields.Int(required=True)


class AnnotatorFullProfile(AnnotatorShortProfile):
    email = fields.Str(required=True)
    creation_date = fields.Date(required=True)
    tasks = fields.List(fields.Nested(TaskShort))


class AnnotatorLockRequest(Schema):
    username = fields.Str(required=True)
    lock_status = fields.Bool(required=True)

