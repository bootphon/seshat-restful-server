from tools.schemas.campaigns import CampaignCreation, CampaignFull, CampaignShort
from .commons import AdminMethodView
from flask_rest_api import Blueprint

campaigns_blp = Blueprint("campaigns", __name__, url_prefix="/campaigns",
                         description="Operations to display and create campaigns")


@campaigns_blp.route("create")
class CreateCampaignHandler(AdminMethodView):

    @campaigns_blp.arguments(CampaignCreation)
    @campaigns_blp.response(code=200)
    def post(self):
        pass


@campaigns_blp.route("list/")
class ListCampaignsHandler(AdminMethodView):

    @campaigns_blp.response(CampaignShort(many=True))
    def get(self):
        pass
