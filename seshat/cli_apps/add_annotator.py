from mongoengine import NotUniqueError

from seshat.configs import set_up_db
from seshat.models.users import Annotator, User
from .commons import argparser

argparser.add_argument("username", type=str, help="Username of created user")
argparser.add_argument("password", type=str, help="Password of created user")
argparser.add_argument("email", type=str, help="Email of created user")
argparser.add_argument("--first_name", default="John",
                       type=str, help="First name of new user")
argparser.add_argument("--last_name", default="Cleese",
                       type=str, help="Last name of new user")


def main():
    args = argparser.parse_args()
    set_up_db(args.config)
    pass_hash, salt = User.create_password_hash(args.password)
    new_user = Annotator(username=args.username,
                         first_name=args.first_name,
                         last_name=args.last_name,
                         email=args.email,
                         salted_password_hash=pass_hash,
                         salt=salt)
    try:
        new_user.save()
    except NotUniqueError:
        print("Error: username or email are not unique")


if __name__ == "__main__":
    main()
