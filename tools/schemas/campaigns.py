from marshmallow import Schema, fields
from .tasks import TaskShort


class CampaignCreation(Schema):
    pass


class CampaignShort(Schema):
    pass


class CampaignFull(Schema):
    tasks = fields.List(fields.Nested(TaskShort))
