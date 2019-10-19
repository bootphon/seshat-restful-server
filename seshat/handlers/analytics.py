from flask_smorest import Blueprint

from .commons import AdminMethodView

analytics_blp = Blueprint("analytics", __name__, url_prefix="/analytics",
                          description="Operations to display and compute analytics on campaigns")


@analytics_blp.route("/basic/<campain_slug>")
class GetBaseAdminStatisticsHandler(AdminMethodView):

    def get(self, campain_slug: str):
        pass


@analytics_blp.route("/complete/<campain_slug>")
class GetCompletedFiles(AdminMethodView):

    def get(self, campain_slug: str):
        pass


@analytics_blp.route("/gamma")
class ComputeFilesetGamma(AdminMethodView):

    def post(self):
        pass
