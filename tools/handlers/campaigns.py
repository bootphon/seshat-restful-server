from .commons import AdminMethodView
from flask_rest_api import Blueprint

campaigns_blp = Blueprint("campaigns", __name__, url_prefix="campaigns/",
                         description="Operations to display and create campaigns")


@campaigns_blp.route("create")
class CreateCampaignHandler(AdminMethodView):
    pass


@campaigns_blp.route("list")
class ListCampaignsHandler(AdminMethodView):
    pass
