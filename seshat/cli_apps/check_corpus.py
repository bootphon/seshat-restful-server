from seshat.configs import set_up_db
from .commons import argparser

argparser.add_argument("-d", "--corpus", type="str", help="Name of the corpus")
argparser.add_argument("-l", "--list", action="store_true", help="List all available corpus")


def main():
    args = argparser.parse_args()
    set_up_db(args.config)

    # TODO


if __name__ == "__main__":
    main()