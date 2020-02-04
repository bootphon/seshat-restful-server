from pathlib import Path

from mongoengine import DoesNotExist

from seshat.configs import set_up_db, BaseConfig
from .commons import argparser

from seshat.models import Campaign
from seshat.models import BaseCorpus, CSVCorpus, FolderCorpus

commands = argparser.add_mutually_exclusive_group()
commands.add_argument("-d", "--corpus", type=str, help="Name of the corpus, lists files found in that corpus")
commands.add_argument("-c", "--campaign", type=str, help="Campaign slug, lists files for that campaign's corpus")
commands.add_argument("-l", "--list", action="store_true", help="List all available corpus")
commands.add_argument("-u", "--update", action="store_true", help="Update the list of corpora")

# TODO : list campaigns for that corpus
# TODO: reorganize the CLI api
# TODO : update files for a given corpus


def list_corpus_files(corpus: BaseCorpus):
    print(f"Files found for corpus {corpus.name}:")
    for file in corpus.files:
        if file.is_valid:
            print(f"\t- {file.filename} : {file.duration}s")
        else:
            print(f"\t- {file.filename} : INVALID ({file.error_msg})")


def main():
    args = argparser.parse_args()
    config: BaseConfig = args.config
    set_up_db(config)

    if args.update:
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

    if args.list or args.update:
        print("Detected Corpora:")
        for corpus in BaseCorpus.objects:
            print(f"\t- \"{corpus.name}\" ({corpus.CORPUS_TYPE}) : {corpus.files_count} files")

    elif args.corpus:
        try:
            corpus: BaseCorpus = BaseCorpus.objects.get(name=args.corpus)
        except DoesNotExist:
            print("Corpus name does not exist")
            return
        if args.corpus:
            corpus.populate_audio_files()
            corpus.save()

        list_corpus_files(corpus)

    elif args.campaign:
        try:
            campaign: Campaign = Campaign.objects.get(name=args.corpus)
        except DoesNotExist:
            print(f"Campaign with slug {args.campaign} does not exist")
            return
        if args.corpus:
            campaign.corpus.populate_audio_files()
            campaign.corpus.save()

        list_corpus_files(campaign.corpus)


if __name__ == "__main__":
    main()