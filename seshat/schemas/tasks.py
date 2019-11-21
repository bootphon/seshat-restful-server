from marshmallow import Schema, fields, validates_schema, ValidationError


class SingleAnnotatorAssignment(Schema):
    annotator = fields.Str(required=True)


class DoubleAnnotatorAssignment(Schema):
    reference = fields.Str(required=True)
    target = fields.Str(required=True)


class TasksAssignment(Schema):
    audio_files = fields.List(fields.Str())
    deadline = fields.Date()
    campaign = fields.Str(required=True)
    single_annot_assign = fields.Nested(SingleAnnotatorAssignment())
    double_annot_assign = fields.Nested(DoubleAnnotatorAssignment())

    @validates_schema
    def validate_data_fields(self, data, **kwargs):
        single_bool = data.get("single_annot_assign") is None
        double_bool = data.get("double_annot_assign") is None
        if single_bool == double_bool:
            raise ValidationError("Task has to be either single xor double annotator")


class TaskLockRequest(Schema):
    task_id = fields.Str(required=True)
    lock_status = fields.Bool(required=True)


class TaskShortStatus(Schema):
    id = fields.Str(required=True)
    from .campaigns import CampaignShortProfile
    campaign = fields.Nested(CampaignShortProfile)
    filename = fields.Str(required=True)
    deadline = fields.Date()
    task_type = fields.Str(required=True)
    annotators = fields.List(fields.Str())
    from .users import UserShortProfile
    assigner = fields.Nested(UserShortProfile, required=True)
    creation_time = fields.DateTime(required=True)
    step = fields.Str(required=True)
    is_locked = fields.Bool(required=True)
    is_done = fields.Bool(required=True)


class TaskTextGrid(Schema):
    name = fields.Str(required=True)
    has_been_submitted = fields.Bool(required=True)
    id = fields.Str()
    from .users import UserShortProfile
    creators = fields.List(fields.Nested(UserShortProfile))
    created = fields.DateTime()


class TaskTextGridList(Schema):
    names = fields.List(fields.Str)


class TaskComment(Schema):
    from .users import UserShortProfile
    author = fields.Nested(UserShortProfile, required=True)
    content = fields.Str(required=True)
    creation = fields.Date(required=True)


class TaskFullStatusAdmin(TaskShortStatus):
    """Task full status """
    from .campaigns import CampaignShortProfile
    campaign = fields.Nested(CampaignShortProfile, required=True)
    textgrids = fields.List(fields.Nested(TaskTextGrid))


class TimeMergeError(Schema):
    tier_a = fields.Str(required=True)
    tier_b = fields.Str(required=True)
    time_a = fields.Int(required=True)
    time_b = fields.Int(required=True)
    index_before = fields.Int(required=True)
    index_after = fields.Int(required=True)
    threshold = fields.Float(required=True)


class DoubleAnnotatorData(Schema):
    from .users import UserShortProfile
    reference = fields.Nested(UserShortProfile, required=True)
    target = fields.Nested(UserShortProfile, required=True)
    current_user_role = fields.Str(required=True)
    #  This field is optional because it's only filled in a double annotator task
    frontiers_merge_table = fields.List(fields.Nested(TimeMergeError))


class TaskFullStatusAnnotator(TaskShortStatus):
    """Task status for the annotator task view"""
    all_steps = fields.List(fields.Str())
    current_step_idx = fields.Int(required=True)
    current_instructions = fields.Str(required=True)
    allow_starter_dl = fields.Bool(required=True)
    allow_file_upload = fields.Bool(required=True)
    double_annot_data = fields.Nested(DoubleAnnotatorData)


class TaskCommentSubmission(Schema):
    content = fields.Str(required=True)


class TaskTextgridSubmission(Schema):
    textgrid_str = fields.Str(required=True)


class AnnotationError(Schema):
    tier = fields.Str(required=True)
    msg = fields.Str(required=True)
    annotation = fields.Str(required=True)
    index = fields.Int(required=True)
    start = fields.Float(required=True)
    end = fields.Float(required=True)


class StructuralError(Schema):
    msg = fields.Str(required=True)


class AnnotMismatchError(Schema):
    ref_tier = fields.Str(required=True)
    target_tier = fields.Str(required=True)
    ref_annot = fields.Str(required=True)
    target_annot = fields.Str(required=True)
    index = fields.Int(required=True)


class TextGridErrors(Schema):
    structural = fields.List(fields.Nested(StructuralError))
    annot_mismatch = fields.List(fields.Nested(AnnotMismatchError))
    time_conflict = fields.List(fields.Nested(TimeMergeError))
    annot = fields.Dict(keys=fields.Str(),
                        values=fields.List(fields.Nested(AnnotationError)))
