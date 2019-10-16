import os

from mongoengine import connect
from flask import Flask
from flask_rest_api import Api

from seshat.configs import DebugConfig, ProductionConfig
from seshat.handlers import *

app = Flask('Seshat API')
app.config.from_object(DebugConfig)
api = Api(app)

if os.environ["FLASK_CONFIG"] == "dev":
    app.config.from_object(DebugConfig)
else:
    app.config.from_object(ProductionConfig)
connect(app.config["MONGODB_SETTINGS"]["db"],
        host=app.config["MONGODB_SETTINGS"]["host"],
        port=app.config["MONGODB_SETTINGS"]["port"], connect=False)

# registering the RESTful API blueprints
api.register_blueprint(accounts_blp)
api.register_blueprint(campaigns_blp)
api.register_blueprint(annotators_blp)
api.register_blueprint(analytics_blp)
api.register_blueprint(tasks_blp)
# This is a regular flask blueprint, so registered on the "unwrapped" app object
app.register_blueprint(downloads_blp)

if __name__ == '__main__':
    app.run()