from seshat.configs import set_up_db
from .commons import argparser
from seshat.parsers import list_parsers

argparser.add_argument("-p", "--parser", type=str, help="Name of the parser, to check its validity")
argparser.add_argument("-l", "--list", action="store_true", help="List all available parsers")


def main():
    args = argparser.parse_args()
    set_up_db(args.config)
    parsers_dict = list_parsers()
    if args.list:
        print("Found %i parsers:" % len(parsers_dict))
        for parser_mod, mod_parsers in parsers_dict.items():
            for parser_name, parser in mod_parsers.items():
                print(f"\t- {parser_name} ({parser_mod})")
    elif args.parser:
        # TODO : check that parser has the required methods, run eventual tests
        try:
            if "." in args.parser:
                parser_mod, parser_name = args.parser.split(".")
                queried_parser_class = parsers_dict[parser_mod][parser_name]
            else:
                for parser_mod, mod_parsers in parsers_dict.items():
                    for parser_name, parser in mod_parsers.items():
                        if parser_name == args.parser_name:
                            queried_parser_class = parser
                            break
                else:
                    raise KeyError()
        except KeyError:
            print(f"Couldn't find parser with name {args.parser}")
            return

        print(f"Found parser {queried_parser_class.get_name()} in module {parser_mod}")
        try:
            parser = queried_parser_class()
        except TypeError as err:
            print(f"The check_parser method hasn't been properly overloaded: {str(err)}")
            return
        print("Checking methods...")
        # checking that the required methods are there, with the right signature
        parse_fn = getattr(queried_parser_class, "parse_annot", None)
        distance_fn = getattr(queried_parser_class, "distance", None)

        # TODO


if __name__ == "__main__":
    main()