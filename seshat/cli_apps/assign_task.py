from mongoengine import connect, DoesNotExist

from seshat.models import Campaign
from .commons import argparser

argparser.add_argument("campaign_slug", type=str, help="Campaign slug for which the task are assigned")
argparser.add_argument("--files", type=str, nargs="*", help="List of files to assign")
group = argparser.add_mutually_exclusive_group(required=True)
group.add_argument("--single", action="store_true")
group.add_argument("--double", action="store_true")
single_group = group.add_argument_group("single annotator task group")
single_group.add_argument("--annotator", type=str)
double_group = group.add_argument_group("double annotators task group")
single_group.add_argument("--target", type=str)
single_group.add_argument("--reference", type=str)


def main():
    args = argparser.parse_args()
    connect(args.db)
    try:
        campaigns: Campaign = Campaign.objects.get(slug=args.campaign_slug)
    except DoesNotExist:
        ValueError("Cannot find campaign with slug %s" % args.campaign_slug)

    # TODO


if __name__ == "__main__":
    main()
