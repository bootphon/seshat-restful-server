import argparse

from mongoengine import connect, NotUniqueError

from seshat.models.users import Admin, Annotator

argparser = argparse.ArgumentParser()
argparser.add_argument("-y", "--confirm", action="store_true",
                       help="Do not ask for confirmation before deleting tasks")
group = argparser.add_mutually_exclusive_group()
group.add_argument("--task_id", type=str, help="Task id")
query_group = group.add_argument_group("filtering query")
query_group.add_argument("--campaign", type=str, help="Campaign in which to look for the task")
query_group.add_argument("--username", type=str, nargs="+", help="Usernames of annotator assigned to task")
query_group.add_argument("--filename", type=str, nargs="+", help="Filenames associated to tasks")


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
