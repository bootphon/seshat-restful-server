import logging

from mongoengine import NotUniqueError, DoesNotExist

from seshat.configs import set_up_db
from seshat.models.users import Admin, Annotator
from .commons import argparser

argparser.add_argument("username", type=str, help="Username of created user")


def main():
    args = argparser.parse_args()
    set_up_db(args.config)

    try:
        annotator: Annotator = Annotator.objects.get(username=args.username)
    except DoesNotExist:
        raise ValueError("User not found")

    annotator.delete()
    logging.info("User deleted")


if __name__ == "__main__":
    main()
