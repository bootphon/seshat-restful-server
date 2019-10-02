from marshmallow import Schema, fields, validates, ValidationError, validates_schema
from marshmallow import validate

from .tasks import TaskShort


class CorporaListing(Schema):
    folders_corpora = fields.List(fields.Str())
    csv_corpora = fields.List(fields.Str())


class TierSpecifications(Schema):
    validate_tier = fields.Bool()
    name = fields.Bool()
    content_type = fields.Str()
    # used if the content type is categorical
    categories = fields.List(fields.Str())
    parser_name = fields.Str()

    @validates("content_type")
    def validate_content_type(self, value: str):
        if value not in ("CATEGORIES", "PARSED"):
            raise ValidationError("Invalid content type category.")


class CampaignCreation(Schema):
    name = fields.Str(required=True, validate=validate.Length(max=100))
    description = fields.Str()
    # these two field are exclusive to one another
    # TODO : validate that one XOR the other is present
    data_csv = fields.Str()
    data_folder = fields.Str()
    enable_audio_dl = fields.Bool(required=True)
    check_textgrids = fields.Bool(default=True)
    checking_scheme = fields.List(fields.Nested(TierSpecifications))

    @validates_schema
    def validate_data_fields(self, data):
        if data.get("data_csv") is not None and data.get("data_folder") is not None:
            raise ValidationError("Data has to be either CSV or a folder but not both")


class CampaignShort(Schema):
    name = fields.Str(required=True)
    total_tasks = fields.Int(required=True)
    completed_tasks = fields.Int(required=True)
    total_files = fields.Int(required=True)
    completed_files = fields.Int(required=True)
    corpus_path = fields.Str(required=True)
    tiers_number = fields.Int(required=True)
    check_textgrid = fields.Bool(required=True)


class CampaignFull(CampaignShort):
    tasks = fields.List(fields.Nested(TaskShort))


class CampaignWikiPage(Schema):
    content = fields.Str()
