import logging
from csv import DictReader
from datetime import datetime
from io import StringIO
from pathlib import Path
from typing import List

import ffmpeg
from mongoengine import Document, StringField, EmbeddedDocument, FloatField, DateTimeField, \
    EmbeddedDocumentListField, BooleanField

from seshat.configs import get_config


class AudioFile(EmbeddedDocument):
    filename: str = StringField(required=True)
    duration: float = FloatField(required=True)
    is_valid: bool = BooleanField(required=True, default=True)
    error_msg: str = StringField()

    def to_msg(self):
        return {
            "filename": self.filename,
            "duration": self.duration,
            "is_valid": self.is_valid,
            "error_msg": self.error_msg
        }


class BaseCorpus(Document):
    CORPUS_TYPE = "BASE CORPUS"
    meta = {'allow_inheritance': True}
    name = StringField(primary_key=True, required=True)
    files: List[AudioFile] = EmbeddedDocumentListField(AudioFile, default=[])
    last_refresh = DateTimeField(default=datetime.now)

    @property
    def real_corpus_path(self):
        return Path(get_config().CAMPAIGNS_FILES_ROOT) / Path(self.name)

    @property
    def exists(self):
        raise NotImplemented()

    @staticmethod
    def list_corpus_csv(path: Path):
        """Lists all the available CSV in the corpora folder, checking beforehand
        that they're valid."""
        return [filepath.name
                for filepath in path.iterdir()
                if filepath.is_file() and filepath.suffix == ".csv"]

    @staticmethod
    def list_subdirs(path: Path):
        """Lists all subdirs of a dir, whithout the root dir's path"""
        return [f.name for f in path.iterdir() if f.is_dir()]

    @staticmethod
    def populate_corpora() -> List['BaseCorpus']:
        """Parses the specified corpora folder and looks for valid corpus folders/files"""
        root_corpus_path = Path(get_config().CAMPAIGNS_FILES_ROOT)
        found_corpora = []
        for filepath in root_corpus_path.iterdir():
            if filepath.is_dir():
                found_corpora.append(FolderCorpus(name=filepath.name))
            elif filepath.is_file() and filepath.suffix == ".csv":
                found_corpora.append(CSVCorpus(name=filepath.name))
        return found_corpora

    @property
    def files_count(self):
        return len([self.files for file in self.files if file.is_valid])

    def get_audio_file_duration(self, filename: str):
        for audio_file in self.files:
            if filename == audio_file.filename:
                return audio_file.duration
        raise ValueError("Couldn't find audio file in corpus")

    def get_file(self, filename: str):
        for audio_file in self.files:
            if filename == audio_file.filename:
                return audio_file
        raise ValueError("Couldn't find audio file in corpus")

    def populate_audio_files(self):
        raise NotImplemented()

    @property
    def short_summary(self):
        return {
            "path": self.name,
            "type": self.CORPUS_TYPE,
            "files_count": self.files_count,
            "last_refreshed": self.last_refresh
        }

    @property
    def full_summary(self):
        return {**self.short_summary, "files": [file.to_msg() for file in self.files]}


class FolderCorpus(BaseCorpus):
    CORPUS_TYPE = "FOLDER"

    @property
    def exists(self):
        return self.real_corpus_path.is_dir()

    @staticmethod
    def extract_ffprob_err(filepath: str, ffprobe_stderr: str):
        """Looks for the right error line in the messy ffprobe output
        The first line starting with the filename is considered to be the right one"""
        for line in StringIO(ffprobe_stderr):
            if line.startswith(filepath):
                return line

    def populate_audio_files(self):
        self.files = []
        authorized_extensions = get_config().SUPPORTED_AUDIO_EXTENSIONS
        for filepath in self.real_corpus_path.glob("**/*"):
            if filepath.suffix.strip(".").lower() not in authorized_extensions:
                continue

            try:
                ffprobe_output = ffmpeg.probe(str(filepath))["format"]["duration"]
                duration = float(ffprobe_output)
                is_valid = True
                error_msg = None

            except ffmpeg.Error as err:
                is_valid = False
                error_msg = ("Ignored because FFprobe returned an error : "
                             + self.extract_ffprob_err(str(filepath), err.stderr.decode('utf-8')))
                duration = 0.0

            except ValueError:
                is_valid = False
                duration = 0.0
                error_msg = f"Ignored because Seshat couldn't convert ffprobe output \"{ffprobe_output}\" to float"

            filename = str(Path(*filepath.parts[1:]))
            self.files.append(AudioFile(filename=filename, duration=duration, error_msg=error_msg, is_valid=is_valid))


class CSVCorpus(BaseCorpus):
    CORPUS_TYPE = "CSV"

    @property
    def exists(self):
        return self.real_corpus_path.is_file() and self.real_corpus_path.suffix == ".csv"

    def populate_audio_files(self):
        self.files = []
        with open(str(self.real_corpus_path), "r") as csv_data_file:
            reader = DictReader(csv_data_file, skipinitialspace=True)
            if not set(reader.fieldnames) == {"filename", "duration"}:
                logging.warning(f"The CSV corpora file {self.name} doesn't "
                                f"have the right headers (filename and duration)")
                return

            for row in reader:
                try:
                    duration = float(row["duration"])
                    is_valid = True
                    error_msg = None

                except ValueError:
                    duration = 0.0
                    is_valid = False
                    error_msg = "Ignored because duration is not a valid float"
                else:
                    if not row["filename"].strip():
                        duration = 0.0
                        is_valid = False
                        error_msg = "Filename is empty"

                    elif not duration:
                        duration = 0.0
                        is_valid = False
                        error_msg = "Ignored because duration is 0 seconds"

                self.files.append(AudioFile(filename=row["filename"],
                                            duration=duration,
                                            is_valid=is_valid,
                                            error_msg=error_msg))
