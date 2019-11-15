import os
from mongoengine import connect

class BaseConfig:
    SUPPORTED_AUDIO_EXTENSIONS = ["wav", "mp3", "ogg", "flac"]
    SMTP_SERVER_PORT = 587
    OPENAPI_VERSION = "3.0.2"
    OPENAPI_URL_PREFIX = '/doc'
    OPENAPI_REDOC_PATH = '/redoc'
    OPENAPI_SWAGGER_UI_PATH = '/swagger'
    # The following is equivalent to OPENAPI_SWAGGER_UI_VERSION = '3.19.5'
    OPENAPI_SWAGGER_UI_URL = 'https://cdnjs.cloudflare.com/ajax/libs/swagger-ui/3.19.5/'

    # Audio campaign files folder
    CAMPAIGNS_FILES_ROOT = "data/"

    LOGS_FOLDER = "logs/"

    MONGODB_SETTINGS = {
        'db': 'seshat_api_dev',
        'host': '127.0.0.1',
        'port': 27017}


class DebugConfig(BaseConfig):
    """Debug Flask Config """

    # Db Settings
    MONGODB_SETTINGS = {
        'db': 'seshat_api_dev',
        'host': '127.0.0.1',
        'port': 27017}

    # Flask settings
    SECRET_KEY = 'Seshat'
    DEBUG = True

    # Flask-User settings
    USER_APP_NAME = "Seshat API Debug"  # Shown in and email templates and page footers


class ProductionConfig(BaseConfig):
    # Flask settings
    SECRET_KEY = 'Seshat API production'
    DEBUG = False

    # Flask-User settings
    USER_APP_NAME = "Seshat API"  # Shown in and email templates and page footers
    # Db Settings
    MONGODB_SETTINGS = {
        'db': 'seshat_api_prod',
        'host': '127.0.0.1',
        'port': 27017}

    # Audio campaign files folder
    CAMPAIGNS_FILES_ROOT = "data/"


class DockerComposeConfig(BaseConfig):
    # Flask settings
    SECRET_KEY = 'Seshat API production'
    DEBUG = False

    # Flask-User settings
    USER_APP_NAME = "Seshat API"  # Shown in and email templates and page footers
    # Db Settings
    MONGODB_SETTINGS = {
        'db': 'seshat_api_prod',
        'host': 'mongo',
        'port': 27017}

config_mapping = {
    "prod": ProductionConfig,
    "docker": DockerComposeConfig,
    "dev": DebugConfig
}


def get_config():
    """Returns the right config, depending on the set FLASK_CONFIG environment variable.
    Falls back to ProductionConfig if none is found"""
    return config_mapping.get(os.environ.get("FLASK_CONFIG"), ProductionConfig)


def set_up_db(config: BaseConfig):
    """Setting up the database based on a config object"""
    connect(config.MONGODB_SETTINGS["db"],
            host=config.MONGODB_SETTINGS["host"],
            port=config.MONGODB_SETTINGS["port"])