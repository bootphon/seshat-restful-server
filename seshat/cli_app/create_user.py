import hashlib
import os

import argparse
from mongoengine import connect, DoesNotExist
from tools.models.users import Admin, Annotator, User


#  TODO : make this script into an "app" that can be used in the seshat namespace

def create_user(username: str,
                password: str,
                email: str,
                first_name: str,
                last_name: str,
                user_type: str = 'admin',
                db: str = 'seshat_dev'):
    connect(db)
    try:
        _ = User.objects.get(username=username)
        raise RuntimeError("Username already taken")
    except DoesNotExist:
        pass

    salt = os.urandom(16).hex()
    pass_hash = hashlib.pbkdf2_hmac('sha256',
                                    password.encode(),
                                    salt.encode(),
                                    100000).hex()
    user_class = Admin if user_type == "admin" else Annotator
    new_user = user_class(active=True,
                          username=username,
                          first_name=first_name,
                          last_name=last_name,
                          email=email,
                          salted_password_hash=pass_hash,
                          salt=salt)
    new_user.save()


argparser = argparse.ArgumentParser()
argparser.add_argument("username", type=str, help="Username of created user")
argparser.add_argument("password", type=str, help="Password of created user")
argparser.add_argument("email", type=str, help="Email of created user")
argparser.add_argument("--first_name", default="Provençal",
                       type=str, help="First name of new user")
argparser.add_argument("--last_name", default="Le Gaulois",
                       type=str, help="Last name of new user")
argparser.add_argument("--type", default="admin", type=str,
                       choices=["admin", "annotator"])
argparser.add_argument("--db", default="seshat_dev", type=str,
                       help="db name or address")

if __name__ == "__main__":
    args = argparser.parse_args()
    create_user(args.username, args.password, args.email, args.first_name,
                args.last_name, args.type, args.db)
