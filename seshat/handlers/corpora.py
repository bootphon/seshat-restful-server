from flask_smorest import Blueprint

from ..schemas.corpora import CorpusShortSummary, CorpusFullSummary
from .commons import AdminMethodView
from ..models import BaseCorpus, Campaign

corpora_blp = Blueprint("corpora", __name__, url_prefix="/corpora",
                        description="Endpoints to list and update audio corpora")


@corpora_blp.route("/list/all")
class ListCorporaHandler(AdminMethodView):

    @corpora_blp.response(CorpusShortSummary(many=True))
    def get(self):
        return [corpus.short_summary for corpus in BaseCorpus.objects]


@corpora_blp.route("/list/<corpus_name>")
class ListCorpusFilesHandler(AdminMethodView):

    @corpora_blp.response(CorpusFullSummary)
    def get(self, corpus_name: str):
        corpus: BaseCorpus = BaseCorpus.objects.get(name=corpus_name)
        return corpus.full_summary


@corpora_blp.route("/list/for/<campaign_slug>")
class ListCorpusFilesHandler(AdminMethodView):

    @corpora_blp.response(CorpusFullSummary)
    def get(self, campaign_slug: str):
        campaign: Campaign = BaseCorpus.objects.get(slug=campaign_slug)
        corpus_summary = campaign.corpus.full_summary
        for audiofile in corpus_summary["files"]:
            audiofile["tasks_count"] = campaign.tasks_for_file(audiofile["name"])
        return corpus_summary


@corpora_blp.route("/refresh")
class RefreshCorporaHandler(AdminMethodView):

    @corpora_blp.response(code=200)
    def get(self):
        found_corpora = BaseCorpus.populate_corpora()
        # TODO : maybe just retrieve only the paths using a filter
        known_corpora_paths = set(corpus.path for corpus in BaseCorpus.objects)
        # if the corpus isn't already in the DB, populate its audio files,
        # and save it
        for corpus in found_corpora:
            if corpus.path not in known_corpora_paths:
                corpus.populate_audio_files()
                corpus.save()


@corpora_blp.route("/corpus/<corpus_name>")
class RefreshCorpusListingHandler(AdminMethodView):

    @corpora_blp.response(code=200)
    def get(self, corpus_name: str):
        corpus: BaseCorpus = BaseCorpus.objects.get(name=corpus_name)
        corpus.populate_audio_files()
        corpus.save()