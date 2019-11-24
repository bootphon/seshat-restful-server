from flask_smorest import Blueprint
from .commons import AdminMethodView

corpora_blp = Blueprint("corpora", __name__, url_prefix="/corpora",
                          description="Endpoints to list and update audio corpora")


@corpora_blp.route("/list/all")
class ListCorporaHandler(AdminMethodView):

    def get(self):
        pass


@corpora_blp.route("/refresh")
class RefreshCorporaHandler(AdminMethodView):

    def get(self):
        pass


@corpora_blp.route("/list/corpus/<corpus_path>")
class RefreshCorpusListingHandler(AdminMethodView):

    def get(self):
        pass