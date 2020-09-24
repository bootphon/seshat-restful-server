from marshmallow import Schema, fields, validates, ValidationError, validates_schema
from marshmallow import validate

from seshat.schemas.users import UserShortProfile


class ParserClass(Schema):
    name = fields.Str(required=True)
    module = fields.Str(required=True)


class TierSpecifications(Schema):
    """Tier checking's specifications"""
    required = fields.Bool(required=True)
    allow_empty = fields.Bool(default=True)
    name = fields.Str(required=True)
    checking_type = fields.Str()
    # used if the content type is categorical
    categories = fields.List(fields.Str())
    # used if the content type is parsed
    parser = fields.Nested(ParserClass)

    @validates("checking_type")
    def validate_checking_type(self, value: str):
        if value not in ("CATEGORICAL", "PARSED", "NONE"):
            raise ValidationError("Invalid checking_type category.")


class CampaignCreation(Schema):
    name = fields.Str(required=True, validate=validate.Length(max=100))
    description = fields.Str(required=True)
    # these two field are exclusive to one another
    corpus = fields.Str(required=True)
    enable_audio_dl = fields.Bool(required=True)
    check_textgrids = fields.Bool(default=True)
    checking_scheme = fields.List(fields.Nested(TierSpecifications))
    # Used when "importing" a TCS from another campaign
    checking_scheme_id = fields.Str()

    @validates_schema
    def validate_data_fields(self, data, **kwargs):
        if data.get("data_csv") is not None and data.get("data_folder") is not None:
            raise ValidationError("Data has to be either CSV or a folder but not both")
        if not data.get("checking_scheme") and not data.get("checking_scheme_id"):
            raise ValidationError("A Checking scheme or a checking scheme ID has to be specified")



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
    tiers_gamma = fields.Mapping(fields.Str, fields.Float)
    can_update_gamma = fields.Bool()
    can_compute_gamma = fields.Bool(required=True)
    gamma_updating = fields.Bool()


class CampaignShortProfile(Schema):
    slug = fields.Str(required=True)
    name = fields.Str(required=True)


class CampaignStatus(Schema):
    slug = fields.Str(required=True)
    name = fields.Str(required=True)
    description = fields.Str(required=True)
    creator = fields.Nested(UserShortProfile, required=True)
    stats = fields.Nested(CampaignStats)
    corpus_path = fields.Str(required=True)
    tiers_number = fields.Int()
    check_textgrids = fields.Bool(required=True)
    from .users import UserShortProfile
    annotators = fields.List(fields.Nested(UserShortProfile))
    subscribers = fields.List(fields.Str)
    creation_time = fields.DateTime(required=True)
    last_update_time = fields.DateTime(required=True)


class CampaignWikiPageUpdate(Schema):
    content = fields.Str(required=True)


class CampaignWikiPage(Schema):
    content = fields.Str(required=True)
    profile = fields.Nested(CampaignShortProfile, required=True)
    last_edit = fields.DateTime()


class CampaignSubscriptionUpdate(Schema):
    slug = fields.Str(required=True)
    # true is subscribe, false is unsubscribe
    subscription_status = fields.Bool(required=True)


class CheckingSchemeSummary(Schema):
    id = fields.Str(required=True)
    name = fields.Str(required=True)
    tier_specs = fields.List(fields.Nested(TierSpecifications))


class TierQuickCheck(Schema):
    tier_name = fields.Str(required=True)
    annotation = fields.Str(required=True)


class QuickCheckResponse(Schema):
    is_valid = fields.Bool(required=True)
    error_msg = fields.Str()