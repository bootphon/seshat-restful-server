from marshmallow import Schema, fields, validates_schema, ValidationError


class SingleAnnotatorAssignment(Schema):
    annotator = fields.Str(required=True)


class DoubleAnnotatorAssignment(Schema):
    reference = fields.Str(required=True)
    target = fields.Str(required=True)


class TaskAssignment(Schema):
    audio_files = fields.List(fields.Str())
    deadline = fields.Date()
    campaign = fields.Str(required=True)
    single_annot_assign = fields.Nested(SingleAnnotatorAssignment())
    double_annot_assign = fields.Nested(DoubleAnnotatorAssignment())

    @validates_schema
    def validate_data_fields(self, data):
        single_bool = data.get("single_annot_assign") is None
        double_bool = data.get("double_annot_assign") is None
        if single_bool == double_bool:
            raise ValidationError("Task has to be either single xor double annotator")


class TaskLockRequest(Schema):
    task_id = fields.Str(required=True)
    lock_status = fields.Bool(required=True)


class TaskShort(Schema):
    filename = fields.Str(required=True)
    deadline = fields.Date()
    task_type = fields.Str(required=True)
    annotators = fields.List(fields.Str())
    assigner = fields.Str(required=True)
    creation_time = fields.DateTime(required=True)
    status = fields.Str(required=True)


class TaskTextGrid(Schema):
    name = fields.Str(required=True)
    is_done = fields.Bool(required=True)


class TaskComment(Schema):
    from .users import UserShortProfile
    author = fields.Nested(UserShortProfile, required=True)
    content = fields.Str(required=True)
    creation = fields.Date(required=True)


class TaskFullAdmin(TaskShort):
    """Task full status """
    textgrids = fields.List(fields.Nested(TaskTextGrid))
    comments = fields.List(fields.Nested(TaskComment))


class FrontierMergeConflict(Schema):
    time_a = fields.Float(required=True)
    time_b = fields.Float(required=True)
    interval_index_before = fields.Int(required=True)
    interval_index_after = fields.Int(required=True)


class TierMergeConflicts(Schema):
    tier_a = fields.Str(required=True)
    tier_b = fields.Str(required=True)
    frontiers_merge = fields.List(fields.Nested(FrontierMergeConflict))


class MergeConflicts(Schema):
    tiers_merges = fields.List(fields.Nested(TierMergeConflicts))


class TaskFullAnnotator(TaskShort):
    """Task status for the annotator task view"""
    all_statuses = fields.List(fields.Str())
    current_status_idx = fields.Int(required=True)
    allow_starter_dl = fields.Bool(required=True)
    allow_file_upload = fields.Bool(required=True)
    # optional because when null, no file should be available for DL
    current_tg_download = fields.Str()
    #  This field is optional because it's only filled in a double annotator task
    frontiers_merge_table = fields.Nested(MergeConflicts)


class TaskCommentSubmission(Schema):
    content = fields.Str(required=True)


class TaskTextgridSubmission(Schema):
    textgrid_str = fields.Str(required=True)


class AnnotationErrors(Schema):
    pass


class StructuralError(Schema):
    pass


class TextgridErrors(Schema):
    # TODO: add merge error and annotation mismatch errors
    structural_errors = fields.List(fields.Nested(StructuralError))
    annot_errors = fields.Dict(keys=fields.Str(),
                               values=fields.Nested(AnnotationErrors))
