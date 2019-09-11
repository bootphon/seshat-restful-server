from .commons import AdminMethodView
from flask_rest_api import Blueprint

campaigns_blp = Blueprint("campaigns", __name__, url_prefix="/campaigns",
                         description="Operations to display and create campaigns")


@campaigns_blp.route("create")
class CreateCampaignHandler(AdminMethodView):

    def post(self):
        pass


@campaigns_blp.route("list/<campaign_slug>")
class ListCampaignsHandler(AdminMethodView):

    def get(self, campaign_slug: str):
        pass
