import logging
from csv import DictReader
from datetime import datetime
from pathlib import Path
from typing import Dict, List

import ffmpeg
from mongoengine import Document, StringField, EmbeddedDocument, FloatField, MapField, DateTimeField, \
    EmbeddedDocumentField

from seshat.configs import get_config


class AudioFile(EmbeddedDocument):
    filename: str = StringField(required=True)
    duration: float = FloatField(required=True)

    def to_msg(self):
        return {
            "filename": self.filename,
            "duration": self.duration
        }


class BaseCorpus(Document):
    CORPUS_TYPE = "BASE CORPUS"
    meta = {'allow_inheritance': True}
    name = StringField(primary_key=True, required=True)
    files: Dict[str, AudioFile] = MapField(EmbeddedDocumentField(AudioFile), default={})
    last_refresh = DateTimeField(default=datetime.now)

    @property
    def real_corpus_path(self):
        return Path(get_config().CAMPAIGNS_FILES_ROOT) / Path(self.name)

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
        return len(self.files)

    def get_audio_file_duration(self, filename: str):
        return self.files[filename].duration

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
        return {**self.short_summary, "files": [file.to_msg() for file in self.files.values()]}


class FolderCorpus(BaseCorpus):
    CORPUS_TYPE = "FOLDER"

    def populate_audio_files(self):
        authorized_extensions = get_config().SUPPORTED_AUDIO_EXTENSIONS
        for filepath in self.real_corpus_path.glob("**/*"):
            if filepath.suffix.strip(".").lower() not in authorized_extensions:
                continue

            try:
                duration = float(ffmpeg.probe(str(filepath))["format"]["duration"])
            except ffmpeg.Error as err:
                logging.warning(f"Dropping file ${str(filepath)} because FFprobe returned an error :"
                                + err.stderr.decode('utf-8'))
                continue
            except ValueError:
                continue
            filename = str(Path(*filepath.parts[1:]))
            self.files[filename] = AudioFile(filename=filename, duration=duration)


class CSVCorpus(BaseCorpus):
    CORPUS_TYPE = "CSV"

    def populate_audio_files(self):
        with open(str(self.real_corpus_path), "r") as csv_data_file:
            reader = DictReader(csv_data_file)
            if not set(reader.fieldnames) == {"filename", "duration"}:
                logging.warning(f"The CSV corpora file ${self.name} doesn't "
                                f"have the right headers (filename and duration)")
                return

            for row in reader:
                try:
                    duration = float(row["duration"])
                except ValueError:
                    logging.warning(f"Dropping file ${row['filename']} because duration is not a valid float")
                    continue

                if not duration:
                    logging.warning(f"Dropping file ${row['filename']} because duration is 0 seconds")
                    continue

                self.files[row["filename"]] = AudioFile(filename=row["filename"],
                                                        duration=duration)



