from seshat.configs import set_up_db
from .commons import argparser

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
    set_up_db(args.config)

    # TODO


if __name__ == "__main__":
    main()
