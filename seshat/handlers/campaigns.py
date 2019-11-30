from typing import Dict

import slugify
from flask_smorest import Blueprint, abort
from mongoengine import ValidationError, NotUniqueError

from seshat.models import BaseCorpus
from seshat.models.tg_checking import TextGridCheckingScheme, ParsedTier
from seshat.parsers import list_parsers
from seshat.parsers.base import AnnotationError
from seshat.schemas.campaigns import CampaignSlug, CampaignEditSchema, CampaignSubscriptionUpdate, \
    CampaignWikiPageUpdate, CheckingSchemeSummary, TierQuickCheck, QuickCheckResponse, ParserClass
from seshat.schemas.tasks import TaskShortStatus
from .commons import AdminMethodView
from .commons import LoggedInMethodView
from ..models.campaigns import Campaign
from ..schemas.campaigns import CampaignCreation, CampaignStatus, CampaignWikiPage

campaigns_blp = Blueprint("campaigns", __name__, url_prefix="/campaigns",
                          description="Operations to display and create campaigns")


@campaigns_blp.route("parsers/list/")
class AvailableParsersHandler(AdminMethodView):

    @campaigns_blp.response(ParserClass(many=True))
    def get(self):
        parsers = []
        for mod_name, parsers_dict in list_parsers().items():
            for parser_name, parser_class in parsers_dict.items():
                parsers.append({"name": parser_name, "module": mod_name})
        return parsers


@campaigns_blp.route("admin/")
class CampaignAdminHandler(AdminMethodView):

    @campaigns_blp.arguments(CampaignCreation)
    @campaigns_blp.response(CampaignSlug, code=200)
    def post(self, args: Dict):
        """Creates a new campaign"""
        if args["check_textgrids"]:
            try:
                checking_scheme: TextGridCheckingScheme = TextGridCheckingScheme.from_tierspecs_schema(
                    scheme_data=args["checking_scheme"],
                    scheme_name=args["name"])
                checking_scheme.validate()
            except ValidationError as e:
                return abort(403, message="Invalid tier specifications : %s" % str(e))
        else:
            checking_scheme = None

        try:
            corpus: BaseCorpus = BaseCorpus.objects.get(name=args["corpus"])
            campaign_slug = slugify.slugify(args["name"])
            wiki_page = "# %s's wiki page\n\nNothing for now..." % args["name"]
            new_campaign = Campaign(name=args["name"],
                                    slug=campaign_slug,
                                    description=args["description"],
                                    corpus=corpus,
                                    check_textgrids=args["check_textgrids"],
                                    serve_audio=args["enable_audio_dl"],
                                    wiki_page=wiki_page,
                                    creator=self.user,
                                    subscribers=[self.user])
            # Force insert forces the insertion of a new campaign.
            # If there already is one with that slug, will raise an error
            new_campaign.save(force_insert=True)
            if checking_scheme is not None:
                checking_scheme.save()
            new_campaign.checking_scheme = checking_scheme
            new_campaign.save()
            return {"slug": new_campaign.slug}
        except NotUniqueError as err:
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

    @campaigns_blp.response(CampaignStatus(many=True))
    def get(self):
        """List all created campaigns, in summary form"""
        return [campaign.status for campaign in Campaign.objects]


@campaigns_blp.route("view/<campaign_slug>")
class ViewCampaignHandler(AdminMethodView):

    @campaigns_blp.response(CampaignStatus)
    def get(self, campaign_slug: str):
        """Returns the full campaign data"""
        campaign: Campaign = Campaign.objects.get(slug=campaign_slug)
        return campaign.status


@campaigns_blp.route("list/tasks/<campaign_slug>")
class ListCampaignTasksHandler(AdminMethodView):

    @campaigns_blp.response(TaskShortStatus(many=True))
    def get(self, campaign_slug: str):
        """Returns the full campaign data"""
        campaign: Campaign = Campaign.objects.get(slug=campaign_slug)
        return [task.short_status for task in campaign.tasks]


@campaigns_blp.route("wiki/update/<campaign_slug>")
class WikiUpdateHandler(AdminMethodView):

    @campaigns_blp.arguments(CampaignWikiPageUpdate, as_kwargs=True)
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
        return {"content": campaign.wiki_page,
                "profile": campaign.short_profile}


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


@campaigns_blp.route("/checking_scheme/<campaign_slug>")
class CampaignCheckingScheme(LoggedInMethodView):

    @campaigns_blp.response(CheckingSchemeSummary)
    @campaigns_blp.response(code=200)
    def get(self, campaign_slug: str):
        campaign: Campaign = Campaign.objects.get(slug=campaign_slug)
        if campaign.check_textgrids and campaign.checking_scheme is not None:
            return campaign.checking_scheme.summary
        else:
            return # nothing is returned


@campaigns_blp.route("/quickcheck/<campaign_slug>")
class ParsedTierQuickCheck(LoggedInMethodView):

    @campaigns_blp.arguments(TierQuickCheck, as_kwargs=True)
    @campaigns_blp.response(QuickCheckResponse)
    def get(self, campaign_slug: str, tier_name: str, annotation: str):
        campaign: Campaign = Campaign.objects.get(slug=campaign_slug)
        if not campaign.check_textgrids:
            abort(403, message="No checking scheme for that campaign")
        try:
            tier_specs = campaign.checking_scheme.tiers_specs[tier_name]
        except KeyError:
            return abort(403, message="Checking scheme for campaign %s doesn't have a tier named %s"
                                      % (campaign_slug, tier_name))

        if not isinstance(tier_specs, ParsedTier):
            return abort(403, message="Annotation checking is only for parsed tiers")

        try:
            tier_specs.parser.check_annotation(annotation)
        except AnnotationError as err:
            return {
                "is_valid": False,
                "error_msg": str(err)
            }
        else:
            return {"is_valid": True}
