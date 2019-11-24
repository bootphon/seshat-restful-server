import traceback
from collections import OrderedDict
from datetime import datetime
from io import StringIO
from os import makedirs
from pathlib import Path
from tempfile import NamedTemporaryFile

from flask import current_app as app
from textgrid import TextGrid


def percentage(a, b):
    try:
        return int(a / b * 100)
    except ZeroDivisionError:
        return 0


class Message:
    COLOR_MAPPING = {"error": ("red lighten-2", "error"),
                     "valid": ("light-green lighten-2", "check"),
                     "warning": ("orange lighten-2", "warning")}

    def __init__(self, text: str, msg_type: str):
        assert msg_type in list(self.COLOR_MAPPING.keys())
        self.type = msg_type
        self.color, self.icon = self.COLOR_MAPPING[msg_type]
        self.text = text






class FixSizeOrderedDict(OrderedDict):
    def __init__(self, *args, max=0, **kwargs):
        self._max = max
        super().__init__(*args, **kwargs)

    def __setitem__(self, key, value):
        OrderedDict.__setitem__(self, key, value)
        if self._max > 0:
            if len(self) > self._max:
                self.popitem(False)


class PersistantStringIO(StringIO):
    """StringIO that stores its buffer when you close it, as not to lose
    the data that was written to it"""

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.data: str = None

    def close(self):
        self.data = self.getvalue()
        super().close()


def open_str_textgrid(textgrid_str: str) -> TextGrid:
    """Since the textgrid librairy only can open TextGrid from an actual file
    (and not a TextIOWrapper type of object), this function enables us to parse
    a TextGrid directly from a string, using a temporary file."""
    with NamedTemporaryFile(mode="w") as temptg:
        temptg.write(textgrid_str)
        temptg.flush()
        return TextGrid.fromFile(temptg.name)


def tg_to_str(textgrid: TextGrid) -> str:
    """Uses a StringIO to write the textgrid into a string instead of into
    a file"""
    str_io = PersistantStringIO()
    textgrid.write(str_io)
    return str_io.data


def consecutive_couples(iterable):
    firsts = list(iterable)
    firsts.pop(-1)
    seconds = list(iterable)
    seconds.pop(0)
    for first, second in zip(firsts, seconds):
        yield first, second


def textfile_decode(file_content: bytes):
    try:
        return file_content.decode("utf-8")
    except UnicodeDecodeError:
        # attempting at decoding using utf-16be
        textgrid_content = file_content.decode("utf-16be")
        # stripping it of that useless byte-order mark thing
        return textgrid_content.strip("\ufeff")


def log_tgcheck_error(error: Exception, textgrid: bytes):
    logdir = (Path(app.config["LOGS_FOLDER"])
              / Path("%s %s" % (str(datetime.now()), str(error))))
    try:
        makedirs(str(logdir))
    except FileExistsError:
        pass
    with open(logdir / Path("stacktrace.txt"), "w") as st_file:
        st_file.write(traceback.format_exc())

    with open(logdir / Path("textgrid.TextGrid"), "wb") as tg_file:
        tg_file.write(textgrid)
