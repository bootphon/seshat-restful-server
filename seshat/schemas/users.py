from marshmallow import Schema, fields


class LoginCredentials(Schema):
    login = fields.Str(required=True)
    password = fields.String(required=True)


class ConnectionToken(Schema):
    token = fields.Str(required=True)


class NotificationData(Schema):
    notid_id = fields.Str(required=True)
    time = fields.DateTime(required=True)
    message = fields.Str(required=True)
    object_type = fields.Str(required=True)
    object_id = fields.Str(required=True)
    notif_type = fields.Str(required=True)


class NotificationsCount(Schema):
    count = fields.Int(required=True)


class NotificationDelete(Schema):
    notif_id = fields.Str(required=True)


class AnnotatorCreation(Schema):
    first_name = fields.Str(required=True)
    last_name = fields.Str(required=True)
    username = fields.Str(required=True)
    password = fields.Str(required=True)
    email = fields.Email(required=True)


class AnnotatorEdition(Schema):
    first_name = fields.Str(required=True)
    last_name = fields.Str(required=True)
    username = fields.Str(required=True)
    email = fields.Email(required=True)


class AnnotatorPasswordChange(Schema):
    username = fields.Str(required=True)
    password = fields.Str(required=True)


class AnnotatorDeletion(Schema):
    username = fields.Str(required=True)


class UserShortProfile(Schema):
    fullname = fields.Str(required=True)
    first_name = fields.Str(required=True)
    last_name = fields.Str(required=True)
    email = fields.Str(required=True)
    username = fields.Str(required=True)
    type = fields.Str(required=True)


class AnnotatorProfile(UserShortProfile):
    last_activity = fields.DateTime(required=True)
    assigned_tasks = fields.Int(required=True)
    active_tasks = fields.Int(required=True)
    finished_tasks = fields.Int(required=True)
    email = fields.Str(required=True)
    creation_date = fields.Date(required=True)
    is_locked = fields.Bool(required=True)


class AnnotatorLockRequest(Schema):
    username = fields.Str(required=True)
    lock_status = fields.Bool(required=True)
