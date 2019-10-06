class BaseConfig:
    # TODO: change password of this before opening the code...
    MAILING_ACCOUNT0_ADDRESS = "seshat@hadware.ovh"
    MAILING_ACCOUNT0_PASSWORD = "seshatandthoth"
    SMTP_SERVER_ADDRESS = "SSL0.OVH.NET"
    SUPPORTED_AUDIO_EXTENSIONS = ["wav", "mp3", "ogg", "flac"]
    SMTP_SERVER_PORT = 587
    OPENAPI_VERSION = "3.0.2"
    OPENAPI_URL_PREFIX = '/doc'
    OPENAPI_REDOC_PATH = '/redoc'
    OPENAPI_SWAGGER_UI_PATH = '/swagger'
    # The following is equivalent to OPENAPI_SWAGGER_UI_VERSION = '3.19.5'
    OPENAPI_SWAGGER_UI_URL = 'https://cdnjs.cloudflare.com/ajax/libs/swagger-ui/3.19.5/'


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

    # network sertings
    HOST = "0.0.0.0"
    PORT = 5000

    # Flask-User settings
    USER_APP_NAME = "Seshat API Debug"  # Shown in and email templates and page footers

    # Audio campaign files folder
    CAMPAIGNS_FILES_ROOT = "data/"

    LOGS_FOLDER = "logs/"


class ProductionConfig(BaseConfig):
    # Flask settings
    SECRET_KEY = 'Seshat API production'
    DEBUG = False

    # network settings
    HOST = "127.0.0.1"
    PORT = 5000

    # Flask-User settings
    USER_APP_NAME = "Seshat"  # Shown in and email templates and page footers
    # Db Settings
    MONGODB_SETTINGS = {
        'db': 'seshat_api_prod',
        'host': '127.0.0.1',
        'port': 27017}

    # Audio campaign files folder
    CAMPAIGNS_FILES_ROOT = "data/"

    LOGS_FOLDER = "logs/"
