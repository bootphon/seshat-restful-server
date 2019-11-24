from typing import Dict

from mongoengine import Document, StringField, EmbeddedDocument, FloatField, IntField, EmbeddedDocumentListField, \
    MapField


class AudioFile(EmbeddedDocument):
    filename = StringField(required=True)
    duration = FloatField(required=True)


class BaseCorpus(Document):
    TASK_TYPE = "BASE CORPUS"
    meta = {'allow_inheritance': True}
    corpus_path = StringField(primary_key=True, required=True)
    files: Dict[str, AudioFile] = MapField(EmbeddedDocument(AudioFile), default={})

    @staticmethod
    def populate_corpora():
        """Parses the specified corpora folder and looks for valid corpus folders/files"""

    @property
    def files_count(self):
        return len(self.files)

    def get_audio_file_duration(self):
        raise NotImplemented()

    def populate_audio_files(self):
        raise NotImplemented()


class FolderCorpus(BaseCorpus):
    pass


class CSVCorpus(BaseCorpus):
    pass