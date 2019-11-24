from marshmallow import Schema, fields


class CorpusFile(Schema):
    """File information: used for task assignment and corpus listing"""
    path = fields.Str(required=True)
    type = fields.Str(required=True)
    tasks_count = fields.Int()


class CorpusShortSummary(Schema):
    pass


class CorpusFull(Schema):
    pass