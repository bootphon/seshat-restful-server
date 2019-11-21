from seshat.configs import set_up_db
from .commons import argparser
from seshat.parsers import list_parsers

argparser.add_argument("-p", "--parser", type=str, help="Name of the parser")
argparser.add_argument("-l", "--list", action="store_true", help="List all available parsers")


def main():
    args = argparser.parse_args()
    set_up_db(args.config)

    if args.list:
        parsers_dict = list_parsers()
        print("Found %i parsers:" % len(parsers_dict))
        for parser_name in parsers_dict.keys():
            print("\t- %s" % parser_name)
    elif args.parser:
        pass


if __name__ == "__main__":
    main()