from pathlib import Path

from seshat.configs import set_up_db
from .commons import argparser

from seshat.utils import list_corpus_csv, list_subdirs
from seshat.models import Campaign

argparser.add_argument("-d", "--corpus", type=str, help="Name of the corpus")
argparser.add_argument("-l", "--list", action="store_true", help="List all available corpus")


def main():
    args = argparser.parse_args()
    set_up_db(args.config)

    if args.list:
        print("Detected Coropora:")
        for corpus in list_subdirs(Path(args.config.CAMPAIGNS_FILES_ROOT)):
            print("\t- %s (Audio Folder)" % corpus)
        for corpus in list_corpus_csv(Path(args.config.CAMPAIGNS_FILES_ROOT)):
            print("\t- %s (CSV)" % corpus)
    elif args.corpus:
        corpus_path = Path(args.config.CAMPAIGNS_FILES_ROOT) / Path()


if __name__ == "__main__":
    main()