from .commons import AdminMethodView
from flask_rest_api import Blueprint

analytics_blp = Blueprint("analytics", __name__, url_prefix="analytics/",
                          description="Operations to display and compute analytics on campaigns")


class GetBaseAdminStatisticsHandler(AdminMethodView):
    pass


class GetCompletedFiles(AdminMethodView):
    pass


class ComputeFilesetGamma(AdminMethodView):
    pass