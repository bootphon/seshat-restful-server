from typing import Dict, List


def parser_factory(parser_name: str):
    """Uses the importlib to load parser using its name"""
    pass


def get_parser_list() -> Dict[int, str]:
    """Returns a dictionary matching parser id to its defined name"""
    pass


class AnnotationError(Exception):
    pass


class AnnotationChecker:

    def check_annotation(self, annot: str) -> None:
        """Checks the input annotation. Doesn't return anything.
        If the annotation has anything wrong, raises an `AnnotationError` """
        raise NotImplemented()


class BaseCustomParser(AnnotationChecker):
    NAME = None
    """This is the class that all custom parsers should inherit from"""

    @property
    def name(self):
        return self.NAME if self.NAME is not None else self.__class__.__name__


class CategoricalChecker(AnnotationChecker):

    def __init__(self, categories: List[str]):
        self.categories = categories

    def check_annotation(self, annot: str):
        pass
