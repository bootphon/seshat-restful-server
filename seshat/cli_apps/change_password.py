import hashlib
import os

import argparse
from mongoengine import connect
from ..models.users import User

argparser = argparse.ArgumentParser()
argparser.add_argument("username", type=str, help="Username of user")
argparser.add_argument("new_password", type=str, help="New password of user")
argparser.add_argument("--db", type=str, default="seshat_prod", help="DB name")


def main():
    args = argparser.parse_args()
    connect(args.db)
    user = User.objects.get(username=args.username)
    pass_hash, salt = User.create_password_hash(args.new_password)
    user.salt = salt
    user.salted_password_hash = pass_hash
    user.save()


if __name__ == "__main__":
    main()
