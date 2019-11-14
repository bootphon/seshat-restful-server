import os

from mongoengine import connect
from flask import Flask
from flask_cors import CORS
from flask_smorest import Api

from seshat.configs import DebugConfig, ProductionConfig
from seshat.handlers import *

app = Flask('Seshat API')
CORS(app)
app.config.from_object(DebugConfig)
api = Api(app)

if os.environ.get("FLASK_CONFIG") == "prod":
    app.config.from_object(ProductionConfig)
else: # if en isn't setup, fallback to dev
    app.config.from_object(DebugConfig)

connect(app.config["MONGODB_SETTINGS"]["db"],
        host=app.config["MONGODB_SETTINGS"]["host"],
        port=app.config["MONGODB_SETTINGS"]["port"], connect=False)

# registering the RESTful API blueprints
api.register_blueprint(accounts_blp)
api.register_blueprint(campaigns_blp)
api.register_blueprint(annotators_blp)
api.register_blueprint(analytics_blp)
api.register_blueprint(tasks_blp)
# registering download handlers
api.register_blueprint(downloads_blp)

if __name__ == '__main__':
    app.run()