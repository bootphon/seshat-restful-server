from .commons import AdminMethodView
from flask_rest_api import Blueprint

campaigns_blp = Blueprint("campaigns", __name__, url_prefix="campaigns/",
                         description="Operations to display and create campaigns")


class CreateCampaignHandler(AdminMethodView):
    pass


class ListCampaignsHandler(AdminMethodView):
    pass
