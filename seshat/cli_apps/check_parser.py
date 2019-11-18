from seshat.configs import set_up_db
from .commons import argparser

argparser.add_argument("-p", "--parser", type="str", help="Name of the parser")
argparser.add_argument("-l", "--list", action="store_true", help="List all available parsers")


def main():
    args = argparser.parse_args()
    set_up_db(args.config)

    # TODO


if __name__ == "__main__":
    main()