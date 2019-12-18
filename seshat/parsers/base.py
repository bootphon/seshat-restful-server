from typing import List
import abc

class AnnotationError(Exception):
    pass


class AnnotationChecker(abc.ABC):

    @abc.abstractmethod
    def check_annotation(self, annot: str) -> None:
        """Checks the input annotation. Doesn't return anything.
        If the annotation has anything wrong, raises an `AnnotationError` """
        raise NotImplemented()

    def distance(self, annot_a: str, annot_b: str) -> float:
        raise NotImplemented()


class BaseCustomParser(AnnotationChecker):
    """This is the class that all custom parsers should inherit from"""
    NAME = None
    VALID_ANNOT_EXAMPLE = ""
    INVALID_ANNOT_EXAMPLE = ""

    @classmethod
    def get_name(cls):
        return cls.NAME if cls.NAME is not None else cls.__name__


class CategoricalChecker(AnnotationChecker):

    def __init__(self, categories: List[str]):
        self.categories = set(categories)

    def check_annotation(self, annot: str):
        if annot.strip() not in self.categories:
            raise AnnotationError(f"Annotation {annot} not valid: has to be one of {', '.join(self.categories)}")

    def distance(self, annot_a: str, annot_b: str) -> float:
        return 1.0# TODO