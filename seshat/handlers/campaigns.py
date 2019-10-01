from flask_rest_api import Blueprint
from tools.handlers.commons import LoggedInMethodView
from tools.schemas.campaigns import CampaignCreation, CampaignShort, CampaignWikiPage, CorporaListing

from .commons import AdminMethodView

campaigns_blp = Blueprint("campaigns", __name__, url_prefix="/campaigns",
                          description="Operations to display and create campaigns")


@campaigns_blp.route("available_copora")
class AvailableCorporaHandler(AdminMethodView):

    @campaigns_blp.response(CorporaListing)
    def get(self):
        pass


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


@campaigns_blp.route("wiki/update/<campaing_slug>")
class WikiUpdateHandler(AdminMethodView):

    @campaigns_blp.arguments(CampaignWikiPage)
    @campaigns_blp.response(code=200)
    def post(self, args, campaign_slug: str):
        pass


@campaigns_blp.route("wiki/view/<campaign_slug>")
class WikiViewHandler(LoggedInMethodView):

    @campaigns_blp.response(CampaignWikiPage)
    def get(self, campaign_slug: str):
        pass
