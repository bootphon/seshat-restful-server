import argparse
import hashlib
import os

from mongoengine import connect

from tools.models.users import User
from tools.models.campaigns import Campaign

argparser = argparse.ArgumentParser()
argparser.add_argument("username", type=str, help="Username of user")
argparser.add_argument("new_password", type=str, help="New password of user")
argparser.add_argument("--db", type=str, default="seshat_dev", help="DB name")

if __name__ == "__main__":
    args = argparser.parse_args()
    connect(args.db)
    user = User.objects.get(username=args.username)
    salt = os.urandom(16).hex()
    pass_hash = hashlib.pbkdf2_hmac('sha256',
                                    args.new_password.encode(),
                                    salt.encode(),
                                    100000).hex()
    user.salt = salt
    user.salted_password_hash = pass_hash
    user.save()

