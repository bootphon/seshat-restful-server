from seshat.configs import set_up_db
from .commons import argparser

argparser.add_argument("campaign", type=str, help="Campaign for which the task are assigned")
argparser.add_argument("--csv", type=str, help="Filename of CSV output")


def main():
    args = argparser.parse_args()
    set_up_db(args.config)


if __name__ == "__main__":
    main()
