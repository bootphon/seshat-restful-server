import argparse

from mongoengine import connect, NotUniqueError

from seshat.models.users import Admin, Annotator

argparser = argparse.ArgumentParser()
argparser.add_argument("username", type=str, help="Username of created user")

def main():
    args = argparser.parse_args()
    connect(args.db)
    pass_hash, salt = Annotator.create_password_hash(args.password)
    new_user = Admin(username=args.username,
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
