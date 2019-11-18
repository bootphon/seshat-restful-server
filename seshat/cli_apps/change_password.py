from seshat.configs import set_up_db
from .commons import argparser
from ..models.users import User

argparser.add_argument("username", type=str, help="Username of user")
argparser.add_argument("new_password", type=str, help="New password of user")


def main():
    args = argparser.parse_args()
    set_up_db(args.config)
    user = User.objects.get(username=args.username)
    pass_hash, salt = User.create_password_hash(args.new_password)
    user.salt = salt
    user.salted_password_hash = pass_hash
    user.save()


if __name__ == "__main__":
    main()
