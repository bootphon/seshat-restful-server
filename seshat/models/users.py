import hashlib
import os
from datetime import datetime

import jwt
from mongoengine import Document, BooleanField, StringField, ListField, \
    ReferenceField, DateTimeField, EmailField, \
    PULL, CASCADE, signals


class Notification(Document):
    time = DateTimeField(default=datetime.now)
    message = StringField(required=True)
    notif_type = StringField(required=True,
                             choices=["assignment", "comment",
                                      "upload", "finished",
                                      "alert"])
    object_type = StringField(required=True,
                              choices=["task", "user", "campaign", "dashboard"])
    object_id = StringField()

    def to_msg(self):
        return {**self.to_mongo(), "notid_id": self.id}


class User(Document):
    meta = {'allow_inheritance': True}

    # User authentication information
    username = StringField(required=True, primary_key=True)
    salted_password_hash = StringField(required=True)
    salt = StringField(required=True)
    active_token = StringField()

    # User information
    first_name = StringField(default="Prénom")
    last_name = StringField(default="Nom")
    email = EmailField(required=True, unique=True)

    pending_notifications = ListField(ReferenceField(Notification))

    @classmethod
    def post_delete_cleanup(cls, sender, document: 'User', **kwargs):
        """Called upon a post_delete event. Takes care of cleaning up stuff, deleteing the user's
        pending notifications"""
        for notif in document.pending_notifications:
            notif.delete()

    @property
    def full_name(self):
        return self.first_name + " " + self.last_name

    def check_password(self, password: str):
        pass_hash = hashlib.pbkdf2_hmac('sha256',
                                        password.encode(),
                                        self.salt.encode(),
                                        100000).hex()
        return self.salted_password_hash == pass_hash

    def get_token(self):
        from flask import current_app
        token_salt = os.urandom(16).hex()
        token_payload = {"salt": token_salt,
                         "username": self.username}
        token: bytes = jwt.encode(token_payload,
                           current_app.config["SECRET_KEY"],
                           algorithm="HS256")
        self.active_token = token.decode()
        self.save()
        return token

    def delete_token(self):
        self.active_token = None

    def check_token(self, token: str):
        return token == self.active_token

    @staticmethod
    def create_password_hash(password: str):
        salt = os.urandom(16).hex()
        pass_hash = hashlib.pbkdf2_hmac('sha256',
                                        password.encode(),
                                        salt.encode(),
                                        100000).hex()
        return pass_hash, salt

    @property
    def short_profile(self):
        return {"fullname": self.full_name,
                "first_name": self.first_name,
                "last_name": self.last_name,
                "username": self.username,
                "email": self.email,
                "type": self.__class__.__name__.lower()}


class Admin(User):
    pass


class Annotator(User):
    creation_time: datetime = DateTimeField(default=datetime.now)
    assigned_tasks = ListField(ReferenceField('BaseTask'))
    locked = BooleanField(default=False)

    stats = None

    @property
    def last_activity(self):
        if self.assigned_tasks:
            sorted_tasks = sorted(self.assigned_tasks, key=lambda x: x.last_update,
                                  reverse=True)
            return sorted_tasks[0].last_update
        else:
            return None

    @property
    def finished_tasks(self):
        return [task for task in self.assigned_tasks if task.is_done]

    @property
    def active_tasks(self):
        return [task for task in self.assigned_tasks if not task.is_done]

    @property
    def profile(self):
        return {
            **super().short_profile,
            "last_activity": self.last_activity,
            "assigned_tasks": len(self.assigned_tasks),
            "active_tasks": len([task for task in self.assigned_tasks if not task.is_done]),
            "finished_tasks": len([task for task in self.assigned_tasks if task.is_done]),
            "creation_date": self.creation_time.date(),
            "is_locked": self.locked,
        }

    def compute_stats(self):
        pass


from .tasks.single import SingleAnnotatorTask
from .tasks.double import DoubleAnnotatorTask
Notification.register_delete_rule(User, 'pending_notifications', PULL)
Annotator.register_delete_rule(SingleAnnotatorTask, 'annotator', CASCADE)
Annotator.register_delete_rule(DoubleAnnotatorTask, 'reference', CASCADE)
Annotator.register_delete_rule(DoubleAnnotatorTask, 'target', CASCADE)
signals.post_delete.connect(User.post_delete_cleanup, sender=User)
