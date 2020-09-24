import os
from pathlib import Path

from dotenv import load_dotenv
from mongoengine import connect


class BaseConfig:
    SUPPORTED_AUDIO_EXTENSIONS = ["wav", "mp3", "ogg", "flac"]
    SMTP_SERVER_PORT = 587
    API_TITLE = "Seshat API"
    API_VERSION = "v1"
    OPENAPI_VERSION = "3.0.2"
    OPENAPI_URL_PREFIX = '/doc'
    OPENAPI_REDOC_PATH = '/redoc'
    OPENAPI_SWAGGER_UI_PATH = '/swagger'
    # The following is equivalent to OPENAPI_SWAGGER_UI_VERSION = '3.19.5'
    OPENAPI_SWAGGER_UI_URL = 'https://cdnjs.cloudflare.com/ajax/libs/swagger-ui/3.19.5/'

    # Audio campaign files folder
    CAMPAIGNS_FILES_ROOT = "corpora/"

    LOGS_FOLDER = "logs/"

    MONGODB_DB = 'seshat_api_dev'
    MONGODB_HOST = '127.0.0.1'
    MONGODB_PORT = 27017


class DebugConfig(BaseConfig):
    """Debug Flask Config """

    # Db Settings
    MONGODB_DB = 'seshat_api_dev'

    # Flask settings
    SECRET_KEY = 'Seshat'
    DEBUG = True


class ProductionConfig(BaseConfig):
    # Flask settings
    SECRET_KEY = 'Seshat API production'
    DEBUG = False

    # Db Settings
    MONGODB_DB = 'seshat_api_prod'


class DockerComposeConfig(BaseConfig):
    # Flask settings
    SECRET_KEY = 'Seshat API production'
    DEBUG = False

    # Db Settings
    MONGODB_DB = 'seshat_api_prod'
    MONGODB_HOST = "mongo"


config_mapping = {
    "prod": ProductionConfig,
    "docker": DockerComposeConfig,
    "dev": DebugConfig
}


def get_config(flask_config=None):
    """Returns the right config. If not argument is passed, loads the config
     depending on the set FLASK_CONFIG environment variable.
    Falls back to ProductionConfig if none is found"""
    # the "passed argument" way supercedes everything.
    if flask_config is not None:
        config_cls = config_mapping[flask_config]
    else:
        # loading optional dotenv file. It won't override any existing env variables
        load_dotenv(dotenv_path=Path(__file__).absolute().parent.parent / Path(".env"))
        config_name = os.environ.get("FLASK_CONFIG")
        config_cls = config_mapping.get(config_name, ProductionConfig)

    # if the config is for regular production, overloading default attributes
    # based on the env variables or the .env file variables
    if config_cls is ProductionConfig:
        attributes = [att for att in dir(config_cls) if not att.startswith("__")]
        for attr in attributes:
            if os.environ.get(attr) is not None:
                setattr(config_cls, attr, os.environ.get(attr))

    return config_cls


def set_up_db(config: BaseConfig):
    """Setting up the database based on a config object"""
    # the connect argument makes mongoengine connect lazily to the db,
    # thus preventing some troubles on app startup when using uwsgi
    connect(config.MONGODB_DB,
            host=config.MONGODB_HOST,
            port=config.MONGODB_PORT,
            connect=False)
