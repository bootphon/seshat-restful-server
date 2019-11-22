import inspect
import sys
import pkgutil
import importlib
from typing import Dict, Type

from .base import BaseCustomParser


# copied from the python documentation
def iter_namespace(ns_pkg):
    # Specifying the second argument (prefix) to iter_modules makes the
    # returned name an absolute name instead of a relative one. This allows
    # import_module to work without having to do additional modification to
    # the name.
    return pkgutil.iter_modules(ns_pkg.__path__, ns_pkg.__name__ + ".")


def list_parsers() -> Dict[str, Type[BaseCustomParser]]:
    """Searches for all available parsers in this namespace and returns
     a dictionary matching parser name to its class"""
    # retrieving all modules installed in seshat.parsers.* (ignoring the base.py)
    parser_modules = [importlib.import_module(name)
                      for finder, name, is_pkg in iter_namespace(sys.modules[__name__])
                      if is_pkg]
    parsers_dict = {}
    # for each module, inspecting its members to find parsers class types.
    for parser_mod in parser_modules:
        for name, obj in inspect.getmembers(parser_mod):
            if inspect.isclass(obj) and issubclass(obj, BaseCustomParser):
                parsers_dict[obj.get_name()] = obj
    return parsers_dict


def parser_factory(parser_name: str) -> BaseCustomParser:
    """Uses the importlib to load parser using its name"""
    try:
        return list_parsers()[parser_name]()
    except KeyError:
        raise ValueError("Couldn't find parser with matching name")
