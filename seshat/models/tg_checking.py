"""Schemas that define how a TextGrid should be checked"""
from typing import Dict

from mongoengine import Document, StringField, EmbeddedDocumentField, BooleanField, ListField, MapField, \
    EmbeddedDocument
from textgrid import IntervalTier

from seshat.models.errors import error_log
from ..parsers.base import CategoricalChecker, parser_factory, AnnotationError, AnnotationChecker


class TierScheme(EmbeddedDocument):
    meta = {"allow_inheritance": True}
    name = StringField(required=True)
    # tier has to be there for the file to be valid
    required = BooleanField(default=True)
    # empty annotations are authorized
    allow_empty = BooleanField(default=True)

    parser: AnnotationChecker = None

    def check_tier(self, tier: IntervalTier):
        for i, annot in enumerate(tier):
            if not self.allow_empty and annot.mark.strip() == "":
                error_log.log_annot(tier.name, i, annot, "Empty annotations are not authorized in this tier")

            try:
                self.parser.check_annotation(annot.mark)
            except AnnotationError as e:
                error_log.log_annot(tier.name, i, annot, str(e))


class UnCheckedTier(TierScheme):

    def check_tier(self, tier: IntervalTier):
        pass


class CategoricalField(TierScheme):
    categories = ListField(StringField())

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.parser = CategoricalChecker(self.categories)


class ParsedField(TierScheme):
    parser_name = StringField(required=True)

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.parser = parser_factory(self.parser_name)


class TextGridCheckingScheme(Document):
    name = StringField(required=True)
    # mapping: tier_name -> specs
    tiers_specs = MapField(EmbeddedDocumentField(TierScheme))
    # empty tiers can be dropped at mergin
    drop_empty_tiers = BooleanField(default=False)
    # for now this isn't set. In the future it'll be a a pluginizable class that can handle checking outside
    # of the defined generic framework
    tg_checker_name = StringField()

    @classmethod
    def from_tierspecs_schema(cls, scheme_data: Dict, scheme_name: str):
        # TODO
        raise NotImplemented()

    @property
    def required_tiers_names(self):
        return [name for name, specs in self.tiers_specs.items() if specs.required]

    @property
    def all_tiers_names(self):
        return list(self.tiers_specs.keys())

    def get_tier_scheme(self, tier_name: str) -> TierScheme:
        return self.tiers_specs[tier_name]
