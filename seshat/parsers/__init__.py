import inspect
import sys
from typing import Dict, Type

from .base import BaseCustomParser


def list_parsers() -> Dict[str, Type[BaseCustomParser]]:
    """Searches for all available parsers in this namespace and returns
     a dictionary matching parser name to its class"""
    return {obj.name: name
            for name, obj in inspect.getmembers(sys.modules[__name__])
            if inspect.isclass(obj) and issubclass(obj, BaseCustomParser)}


def parser_factory(parser_name: str) -> BaseCustomParser:
    """Uses the importlib to load parser using its name"""
    try:
        return list_parsers()[parser_name]()
    except KeyError:
        raise ValueError("Couldn't find parser with matching name")
