from pathlib import Path
from typing import Dict

import slugify
from flask import current_app
from flask_smorest import Blueprint, abort
from mongoengine import ValidationError, NotUniqueError

from seshat.models.tg_checking import TextGridCheckingScheme
from seshat.schemas.campaigns import CampaignFull, CampaignSlug, CampaignEditSchema, CampaignSubscriptionUpdate
from .commons import AdminMethodView
from .commons import LoggedInMethodView
from ..schemas.campaigns import CampaignCreation, CampaignShort, CampaignWikiPage, CorporaListing
from ..utils import list_subdirs, list_corpus_csv
from ..models.campaigns import Campaign

campaigns_blp = Blueprint("campaigns", __name__, url_prefix="/campaigns",
                          description="Operations to display and create campaigns")


@campaigns_blp.route("available_corpora")
class AvailableCorporaHandler(AdminMethodView):

    @campaigns_blp.response(CorporaListing)
    def get(self):
        """Get a list of available folder and CSV corpora"""
        return {"folders_corpora": list_subdirs(Path(current_app.config["CAMPAIGNS_FILES_ROOT"])),
                "csv_corpora": list_corpus_csv(Path(current_app.config["CAMPAIGNS_FILES_ROOT"]))}


@campaigns_blp.route("admin/")
class CampaignAdminHandler(AdminMethodView):

    @campaigns_blp.arguments(CampaignCreation)
    @campaigns_blp.response(CampaignSlug, code=200)
    def post(self, args: Dict):
        """Creates a new campaign"""
        try:
            checking_scheme: TextGridCheckingScheme = TextGridCheckingScheme.from_tierspecs_schema(
                scheme_data=args["checking_scheme"],
                scheme_name=args["name"])
            checking_scheme.validate()
        except ValidationError as e:
            return abort(403, message="Invalid tier specifications : %s" % str(e))

        try:
            if args.get("data_csv") is not None:
                corpus_path = args["data_csv"]
            else:
                corpus_path = args["data_folder"]
            campaign_slug = slugify.slugify(args["name"])
            new_campaign = Campaign(name=args["name"],
                                    slug=campaign_slug,
                                    description=args["description"],
                                    corpus_path=corpus_path,
                                    check_textgrid=args["check_textgrids"],
                                    serve_audio=args["enable_audio_dl"],
                                    creator=self.user,
                                    subscribers=[self.user])
            new_campaign.save()
            new_campaign.checking_scheme = checking_scheme
            new_campaign.cascade_save()
        except NotUniqueError:
            abort(403, message="The campaign name is too close to another campaign name")
        except ValidationError as e:
            abort(403, "Invalid campaign specifications : %s" % str(e))

    @campaigns_blp.arguments(CampaignSlug, as_kwargs=True)
    @campaigns_blp.response(code=200)
    def delete(self, slug: str):
        """Delete a campaign"""
        campaign: Campaign = Campaign.objects.get(slug=slug)
        campaign.delete()

    @campaigns_blp.arguments(CampaignEditSchema, as_kwargs=True)
    @campaigns_blp.response(code=200)
    def put(self, slug, **kwargs):
        """Update a campaign"""
        campaign: Campaign = Campaign.objects.get(slug=slug)
        campaign.update(**kwargs)
        campaign.save()


@campaigns_blp.route("list/")
class ListCampaignsHandler(AdminMethodView):

    @campaigns_blp.response(CampaignShort(many=True))
    def get(self):
        """List all created campaigns, in summary form"""
        return [campaign.short_summary for campaign in Campaign.objects]


@campaigns_blp.route("view/<campaign_slug>")
class ViewCampaignHandler(AdminMethodView):

    @campaigns_blp.response(CampaignFull)
    def get(self, campaign_slug: str):
        """Returns the full campaign data"""
        campaign: Campaign = Campaign.objects.get(slug=campaign_slug)
        return campaign.full_summary


@campaigns_blp.route("wiki/update/<campaign_slug>")
class WikiUpdateHandler(AdminMethodView):

    @campaigns_blp.arguments(CampaignWikiPage, as_kwargs=True)
    @campaigns_blp.response(code=200)
    def post(self, content: str, campaign_slug: str):
        """Update the campaign's wiki page"""
        campaign: Campaign = Campaign.objects.get(slug=campaign_slug)
        campaign.wiki_page = content
        campaign.save()


@campaigns_blp.route("wiki/view/<campaign_slug>")
class WikiViewHandler(LoggedInMethodView):

    @campaigns_blp.response(CampaignWikiPage)
    def get(self, campaign_slug: str):
        """View a campaign's wiki page"""
        campaign: Campaign = Campaign.objects.get(slug=campaign_slug)
        return {"content": campaign.wiki_page}


@campaigns_blp.route("wiki/view/<campaign_slug>")
class WikiViewHandler(LoggedInMethodView):

    @campaigns_blp.response(CampaignWikiPage)
    def get(self, campaign_slug: str):
        """Retrieve the campaign's wikipage content"""
        campaign: Campaign = Campaign.objects.get(slug=campaign_slug)
        return {"content": campaign.wiki_page}


@campaigns_blp.route("/subscribe")
class CampaignSubscriptionHandler(AdminMethodView):

    @campaigns_blp.arguments(CampaignSubscriptionUpdate, as_kwargs=True)
    @campaigns_blp.response(code=200)
    def post(self, slug: str, subscription_status: bool):
        """Subscribes or unsubscribes an admin from a campaign"""
        campaign: Campaign = Campaign.objects.get(slug=slug)
        if subscription_status:
            if self.user not in campaign.subscribers:
                campaign.subscribers.append(self.user)
                campaign.save()
        else:
            if self.user in campaign.subscribers:
                campaign.subscribers.remove(self.user)
                campaign.save()
