import importlib
import inspect
import pkgutil
from collections import defaultdict
from typing import Dict, Type

from .base import BaseCustomParser


# copied from the python documentation
# https://packaging.python.org/guides/creating-and-discovering-plugins/
def find_parser_packages():
    """Seaches for all installed packages in the namespace that start with `seshat_parser_`"""
    return {
        name: importlib.import_module(name)
        for finder, name, ispkg
        in pkgutil.iter_modules()
        if name.startswith('seshat_parser_') and ispkg
    }


def list_parsers() -> Dict[str, Dict[str, Type[BaseCustomParser]]]:
    """Searches for all available parsers in this namespace and returns
     a dictionary matching parser name to its class"""
    # retrieving all modules installed in seshat.parsers.* (ignoring the base.py)
    parsers_modules = find_parser_packages()
    parsers_dict = defaultdict(dict)
    # for each module, inspecting its members to find parsers class types.
    for mod_name, parser_mod in parsers_modules.items():
        for name, obj in inspect.getmembers(parser_mod):
            if inspect.isclass(obj) and issubclass(obj, BaseCustomParser):
                parsers_dict[mod_name][obj.get_name()] = obj
    return parsers_dict


def parser_factory(parser_mod: str, parser_name: str) -> BaseCustomParser:
    """Uses the importlib to load parser using its name"""
    try:
        return list_parsers()[parser_mod][parser_name]()
    except KeyError:
        raise ValueError("Couldn't find parser with matching name")
