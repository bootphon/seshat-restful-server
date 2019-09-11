import hashlib
import os
from datetime import datetime

from mongoengine import Document, BooleanField, StringField, ListField, \
    ReferenceField, DoesNotExist, DateTimeField, EmailField, \
    PULL

from tools.models.commons import DBError


class Notification(Document):
    time = DateTimeField(default=datetime.now)
    url = StringField(required=True)
    message = StringField(required=True)
    notif_type = StringField(required=True,
                             choices=["assignment", "comment",
                                      "upload", "finished",
                                      "alert"])
    ICON_MAPPING = {
        "assignment": "assignment_returned",
        "comment": "insert_comment",
        "upload": "publish",
        "finished": "assignment_turned_in",
        "alert": "assignment_late"}

    @property
    def icon(self):
        return self.ICON_MAPPING[self.notif_type]


class User(Document):
    meta = {'allow_inheritance': True}
    active = BooleanField(default=True, required=True)

    # User authentication information
    username = StringField(required=True, primary_key=True)
    salted_password_hash = StringField(required=True)
    salt = StringField(required=True)
    # TODO : figure out robust token system

    # User information
    first_name = StringField(default="Prénom")
    last_name = StringField(default="Nom")
    email = EmailField(required=True, unique=True)

    pending_notifications = ListField(ReferenceField(Notification))

    @property
    def full_name(self):
        return self.first_name + " " + self.last_name

    def check_password(self, password: str):
        pass_hash = hashlib.pbkdf2_hmac('sha256',
                                        password.encode(),
                                        self.salt.encode(),
                                        100000).hex()
        return self.salted_password_hash == pass_hash

    def check_token(self, token: str):
        pass

    @staticmethod
    def create_password_hash(password: str):
        salt = os.urandom(16).hex()
        pass_hash = hashlib.pbkdf2_hmac('sha256',
                                        password.encode(),
                                        salt.encode(),
                                        100000).hex()
        return pass_hash, salt


class Admin(User):
    pass


class Annotator(User):
    creation_time = DateTimeField(default=datetime.now)
    assigned_tasks = ListField(ReferenceField('BaseTask'))

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

    @classmethod
    def create(cls,
               username: str,
               password: str,
               first_name: str,
               last_name: str,
               email: str,
               campaign: str):
        try:
            _ = cls.objects.get(username=username)
            raise DBError("Nom d'utilisateur déjà pris")
        except DoesNotExist:
            pass

        if len(password) < 8:
            raise DBError("Mot de passe trop court")

        pass_hash, salt = User.create_password_hash(password)
        new_user = cls(username=username,
                       salted_password_hash=pass_hash,
                       salt=salt,
                       first_name=first_name,
                       last_name=last_name,
                       email=email,
                       assigned_campaign=campaign)
        new_user.save()

        try:
            from .campaigns import Campaign
            campaign_obj = Campaign.objects.get(slug=campaign)
        except DoesNotExist:
            raise DBError("La campagne assignée à l'utilisateur n'existe pas")
        else:
            campaign_obj.annotators.append(new_user)
            campaign_obj.save()

        return new_user

    def reassign_campaign(self, campaign_slug):
        from .campaigns import Campaign
        try:
            # removing former ref
            self.assigned_campaign.annotators.remove(self)
            self.assigned_campaign.save()
        except (AttributeError, ValueError):
            pass

        campaign = Campaign.objects.get(slug=campaign_slug)
        # new assignment
        self.assigned_campaign = campaign
        campaign.annotators.append(self)
        campaign.save()
        self.save()

    def compute_stats(self):
        pass


Notification.register_delete_rule(User, 'pending_notifications', PULL)
