import marshmallow as ma
from flask import Flask, request
from flask.views import MethodView
from flask_rest_api import Api, Blueprint

from tools.handlers.commons import LoggedInMethodView


class Config:
    OPENAPI_VERSION = "3.0.2"
    OPENAPI_URL_PREFIX = '/doc'
    OPENAPI_REDOC_PATH = '/redoc'
    OPENAPI_SWAGGER_UI_PATH = '/swagger'
    # The following is equivalent to OPENAPI_SWAGGER_UI_VERSION = '3.19.5'
    OPENAPI_SWAGGER_UI_URL = 'https://cdnjs.cloudflare.com/ajax/libs/swagger-ui/3.19.5/'


app = Flask('My API')
app.config.from_object(Config)
api = Api(app)


class PetSchema(ma.Schema):
    class Meta:
        strict = True
        ordered = True

    id = ma.fields.Int(dump_only=True)
    name = ma.fields.String()


blp = Blueprint(
    'pets',
    'pets',
    url_prefix='/pets',
    description='Operations on pets'
)


@blp.route('/')
class Pets(LoggedInMethodView):

    @blp.response(PetSchema(many=True))
    def get(self):
        """List pets"""
        return [{"id": 4577, "name": "le crou"}]


api.register_blueprint(blp)

if __name__ == '__main__':
    app.run()