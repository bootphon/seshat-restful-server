from flask_smorest import Blueprint

from .commons import AdminMethodView
from ..models import BaseCorpus, Campaign
from ..schemas.corpora import CorpusShortSummary, CorpusFullSummary

corpora_blp = Blueprint("corpora", __name__, url_prefix="/corpora",
                        description="Endpoints to list and update audio corpora")


@corpora_blp.route("/list/all")
class ListCorporaHandler(AdminMethodView):

    @corpora_blp.response(200, schema=CorpusShortSummary(many=True))
    def get(self):
        """List all available corpora"""
        return [corpus.short_summary for corpus in BaseCorpus.objects]


@corpora_blp.route("/list/<corpus_name>")
class ListCorpusFilesHandler(AdminMethodView):

    @corpora_blp.response(200, schema=CorpusFullSummary)
    def get(self, corpus_name: str):
        """List all the files for an available corpora"""
        corpus: BaseCorpus = BaseCorpus.objects.get(name=corpus_name)
        return corpus.full_summary


@corpora_blp.route("/list/for/<campaign_slug>")
class ListCampaignCorpusFilesHandler(AdminMethodView):

    @corpora_blp.response(200, schema=CorpusFullSummary)
    def get(self, campaign_slug: str):
        """List a corpus files relative to a campaign (with the count of tasks
        already assigned to that file)"""
        campaign: Campaign = Campaign.objects.get(slug=campaign_slug)
        corpus_summary = campaign.corpus.full_summary
        corpus_summary["files"] = list(filter(lambda file: file["is_valid"], corpus_summary["files"]))
        for audiofile in corpus_summary["files"]:
            audiofile["tasks_count"] = campaign.tasks_for_file(audiofile["filename"])
        return corpus_summary


@corpora_blp.route("/refresh")
class RefreshCorporaHandler(AdminMethodView):

    @corpora_blp.response(200)
    def get(self):
        """Ask the server to refresh the existing corpus list from the
        corpus folder"""
        found_corpora = BaseCorpus.populate_corpora()
        # TODO : maybe just retrieve only the paths using a filter
        known_corpora_paths = set(corpus.name for corpus in BaseCorpus.objects)
        # if the corpus isn't already in the DB, populate its audio files,
        # and save it
        for corpus in found_corpora:
            if corpus.name not in known_corpora_paths:
                corpus.populate_audio_files()
                corpus.save()

        # cleaning up deleted corpora not referenced by any campaign
        for corpus in BaseCorpus.objects:
            if corpus.exists:
                continue

            campaigns_with_corpus = Campaign.objects(corpus=corpus).count()
            if campaigns_with_corpus == 0:
                corpus.delete()


@corpora_blp.route("/refresh/<corpus_name>")
class RefreshCorpusListingHandler(AdminMethodView):

    @corpora_blp.response(200)
    def get(self, corpus_name: str):
        """Ask the server to update the corpus files list from the corpus's
        folder or CSV file."""
        corpus: BaseCorpus = BaseCorpus.objects.get(name=corpus_name)
        corpus.populate_audio_files()
        corpus.save()

        # telling all the campaigns that reference that corpus to update their
        # stats, in case files were added/removed
        for campaign in Campaign.objects(corpus=corpus):
            campaign.update_stats()
