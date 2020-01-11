from inspect import signature
from itertools import chain

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
        parsers_count = len(list(chain.from_iterable(parsers_dict.values())))
        print(f"Found {parsers_count:d} parsers in {len(parsers_dict):d} modules:")
        for parser_mod, mod_parsers in parsers_dict.items():
            for parser_name, parser in mod_parsers.items():
                print(f"\t- {parser_name} ({parser_mod})")
    elif args.parser:

        def search_parser(parsers_dict, parser_name):
            for parser_mod, mod_parsers in parsers_dict.items():
                for found_parser_name, parser_class in mod_parsers.items():
                    if parser_name == found_parser_name:
                        return parser_class, parser_mod
            return None, None

        try:
            if "." in args.parser:
                parser_mod, parser_name = args.parser.split(".")
                queried_parser_class = parsers_dict[parser_mod][parser_name]
            else:
                queried_parser_class, parser_mod = search_parser(parsers_dict, args.parser)
                if queried_parser_class is None:
                    raise KeyError()

        except KeyError:
            print(f"Couldn't find parser with name {args.parser}")
            return

        print(f"Found parser {queried_parser_class.get_name()} in module {parser_mod}")
        try:
            parser = queried_parser_class()
        except TypeError as err:
            print(f"The 'check_annotation' method hasn't been properly overloaded: {str(err)}")
            return
        print("Checking methods...")
        # checking that the required methods are there, with the right signature
        parse_fn = getattr(queried_parser_class, "check_annotation", None)
        distance_fn = getattr(queried_parser_class, "distance", None)

        if parse_fn is None:
            print("ERROR: the 'check_annotation' method couldn't be found on that parser")
        else:
            print("Detected 'check_annotation' method")
            parse_sig = signature(parse_fn)
            if len(parse_sig.parameters) != 2:
                print(f"WARNING: the 'check_annotation' method should have only one parameters, "
                      f"found {len(parse_sig.parameters)} parameters")
            else:
                print("Detected 1 parameter for 'check_annotation' (as it should be).")
                print("'check_annotation' method seems to be valid")

        if distance_fn is None:
            print("WARNING: 'distance' method couldn't be found. This means no inter-rater agreement can be computed "
                  "for Tiers checked with this parser")
        else:
            print("Detected a 'distance' method")
            distance_sig = signature(distance_fn)
            if len(distance_sig.parameters) != 3:
                print(f"WARNING: the 'distance' method should have exactly 2 parameters, "
                      f"found {len(distance_sig.parameters)} parameters")
            else:
                print("Detected 2 parameters for 'distance' (as it should be).")
                print("The 'distance' method seems to be valid")

        # TODO : use default annotations to check


if __name__ == "__main__":
    main()