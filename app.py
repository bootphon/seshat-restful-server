from flask import Flask
from flask_cors import CORS
from flask_smorest import Api

from seshat.configs import get_config, set_up_db
from seshat.handlers import *

app = Flask('Seshat API', static_url_path='')
# allowing Cross origin requests
CORS(app)

# retrieving the right config, using the FLASK_CONFIG env variable.
config = get_config()
app.config.from_object(config)
set_up_db(config)

# Wrapping the app with the Smorest Api Object
api = Api(app)

# registering the RESTful API blueprints
api.register_blueprint(accounts_blp)
api.register_blueprint(campaigns_blp)
api.register_blueprint(corpora_blp)
api.register_blueprint(annotators_blp)
api.register_blueprint(analytics_blp)
api.register_blueprint(tasks_blp)
api.register_blueprint(downloads_blp)

# serving the index.html
@app.route('/')
def root():
    return app.send_static_file('index.html')


if __name__ == '__main__':
    app.run()