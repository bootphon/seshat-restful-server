"""Schemas that define how a TextGrid should be checked"""
from typing import List, Dict

from mongoengine import Document, StringField, EmbeddedDocumentField, BooleanField, ListField, MapField, \
    EmbeddedDocument
from textgrid import IntervalTier, TextGrid

from seshat.models.errors import error_log
from ..parsers import parser_factory
from ..parsers.base import CategoricalChecker, AnnotationError, AnnotationChecker


class TierScheme(EmbeddedDocument):
    CHECKING_TYPE = ""
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

    def to_specs(self):
        return {
            "name": self.name,
            "required": self.required,
            "allow_empty": self.allow_empty,
            "checking_type": self.CHECKING_TYPE
        }


class UnCheckedTier(TierScheme):
    CHECKING_TYPE = "NONE"

    def check_tier(self, tier: IntervalTier):
        pass



class CategoricalTier(TierScheme):
    CHECKING_TYPE = "CATEGORICAL"
    categories = ListField(StringField())

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.parser = CategoricalChecker(self.categories)

    def to_specs(self):
        return {**super().to_specs(), "categories": self.categories}


class ParsedTier(TierScheme):
    CHECKING_TYPE = "PARSED"
    parser_name = StringField(required=True)

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.parser = parser_factory(self.parser_name)

    def to_specs(self):
        return {**super().to_specs(), "parser_name": self.parser_name}


class TextGridCheckingScheme(Document):
    name = StringField(required=True)
    # mapping: tier_name -> specs
    tiers_specs: Dict[str, TierScheme] = MapField(EmbeddedDocumentField(TierScheme))
    # empty tiers can be dropped at merging, currently not implemented in the client
    drop_empty_tiers = BooleanField(default=False)
    # for now this isn't set. In the future it'll be a a pluginizable class that can handle checking outside
    # of the defined generic framework
    tg_checker_name = StringField()

    @classmethod
    def from_tierspecs_schema(cls, scheme_data: List, scheme_name: str):
        new_scheme = cls(name=scheme_name)
        for tier_specs in scheme_data:
            if tier_specs.get("checking_type") == "CATEGORICAL":
                new_tier_scheme = CategoricalTier(name=tier_specs["name"],
                                                  required=tier_specs["required"],
                                                  allow_empty=tier_specs["allow_empty"],
                                                  categories=tier_specs["categories"])
            elif tier_specs.get("checking_type") == "PARSED":
                new_tier_scheme = ParsedTier(name=tier_specs["name"],
                                             required=tier_specs["required"],
                                             allow_empty=tier_specs["allow_empty"],
                                             parser_name=tier_specs["parser_name"])

            else:
                new_tier_scheme = UnCheckedTier(name=tier_specs["name"],
                                                allow_empty=tier_specs["allow_empty"],
                                                required=tier_specs["required"])
            new_scheme.tiers_specs[tier_specs["name"]] = new_tier_scheme
        return new_scheme

    @property
    def required_tiers_names(self):
        return [name for name, specs in self.tiers_specs.items() if specs.required]

    @property
    def all_tiers_names(self):
        return list(self.tiers_specs.keys())

    def get_tier_scheme(self, tier_name: str) -> TierScheme:
        return self.tiers_specs[tier_name]

    def gen_template_tg(self, duration: float, filename: str):
        new_tg = TextGrid(name=filename,
                          minTime=0.0,
                          maxTime=duration)
        for tier_name in self.tiers_specs.keys():
            new_tier = IntervalTier(name=tier_name, minTime=0.0, maxTime=duration)
            new_tg.append(new_tier)

        return new_tg

    @property
    def summary(self):
        return {
            "id": str(self.id),
            "name": self.name,
            "tier_specs": [tier.to_specs() for tier in self.tiers_specs.values()]
        }
