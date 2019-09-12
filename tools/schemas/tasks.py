from marshmallow import Schema, fields


class SingleAnnotatorAssignment(Schema):
    annotator = fields.Str(required=True)


class DoubleAnnotatorAssignment(Schema):
    reference = fields.Str(required=True)
    target = fields.Str(required=True)


class TaskAssignment(Schema):
    filename = fields.Str(required=True)
    deadline = fields.Date()
    single_annot_assign = fields.Nested(SingleAnnotatorAssignment())
    double_annot_assign = fields.Nested(DoubleAnnotatorAssignment())


class TaskShort(Schema):
    filename = fields.Str(required=True)
    deadline = fields.Date()
    task_type = fields.Str(required=True)
    annotators = fields.List(fields.Str())
    status = fields.Str(required=True)


class TaskTextGrid(Schema):
    name = fields.Str(required=True)
    is_done = fields.Bool(required=True)


class TaskFullAdmin(TaskShort):
    assigner = fields.Str(required=True)
    creation_date = fields.Str(required=True)
    textgrids = fields.List(fields.Nested(TaskTextGrid))


class TaskFullAnnotator(Schema):
    pass