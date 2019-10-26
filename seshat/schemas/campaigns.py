from marshmallow import Schema, fields, validates, ValidationError, validates_schema
from marshmallow import validate

from seshat.schemas.users import UserShortProfile
from .tasks import TaskShort


class CorporaListing(Schema):
    folders_corpora = fields.List(fields.Str())
    csv_corpora = fields.List(fields.Str())


class TierSpecifications(Schema):
    validate_tier = fields.Bool(required=True)
    required = fields.Bool(required=True)
    allow_empty = fields.Bool(default=True)
    name = fields.Str(required=True)
    content_type = fields.Str()
    # used if the content type is categorical
    categories = fields.List(fields.Str())
    # used if the content type is parsed
    parser_name = fields.Str()

    @validates("content_type")
    def validate_content_type(self, value: str):
        if value not in ("CATEGORIES", "PARSED", "NONE"):
            raise ValidationError("Invalid content type category.")


class CampaignCreation(Schema):
    name = fields.Str(required=True, validate=validate.Length(max=100))
    description = fields.Str()
    # these two field are exclusive to one another
    data_csv = fields.Str()
    data_folder = fields.Str()
    enable_audio_dl = fields.Bool(required=True)
    check_textgrids = fields.Bool(default=True)
    checking_scheme = fields.List(fields.Nested(TierSpecifications))

    # @validates_schema
    # def validate_data_fields(self, data):
    #     if data.get("data_csv") is not None and data.get("data_folder") is not None:
    #         raise ValidationError("Data has to be either CSV or a folder but not both")


class CampaignSlug(Schema):
    slug = fields.Str(required=True)


class CampaignEditSchema(Schema):
    slug = fields.Str(required=True)
    description = fields.Str(required=True)
    name = fields.Str(required=True)


class CampaignStats(Schema):
    total_tasks = fields.Int(required=True)
    completed_tasks = fields.Int(required=True)
    total_files = fields.Int(required=True)
    assigned_files = fields.Int(required=True)


class CampaignShort(Schema):
    slug = fields.Str(required=True)
    name = fields.Str(required=True)
    creator = fields.Nested(UserShortProfile, required=True)
    stats = fields.Nested(CampaignStats)
    corpus_path = fields.Str(required=True)
    tiers_number = fields.Int()
    check_textgrids = fields.Bool(required=True)
    annotators = fields.List(fields.Str())


class CampaignFull(CampaignShort):
    tasks = fields.List(fields.Nested(TaskShort))


class CampaignWikiPage(Schema):
    content = fields.Str(required=True)
    last_edit = fields.DateTime()


class CampaignSubscriptionUpdate(Schema):
    slug = fields.Str(required=True)
    # true is subscribe, false is unsubscribe
    subscription_status = fields.Bool(required=True)
