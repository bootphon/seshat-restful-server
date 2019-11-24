from marshmallow import Schema, fields


class CorpusFile(Schema):
    """File information: used for task assignment and corpus listing"""
    filename = fields.Str(required=True)
    duration = fields.Float(required=True)
    tasks_count = fields.Int()


class CorpusShortSummary(Schema):
    path = fields.Str(required=True)
    type = fields.Str(required=True)
    files_count = fields.Int(required=True)
    last_refreshed = fields.DateTime(required=True)


class CorpusFullSummary(CorpusShortSummary):
    files = fields.List(fields.Nested(CorpusFile))

