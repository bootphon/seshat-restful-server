from mongoengine import DoesNotExist

from seshat.configs import set_up_db
from .commons import argparser

from seshat.models import Campaign

argparser.add_argument("campaign_slug", type=str, help="Slug for which you want to retrieve the gamma summary")
argparser.add_argument("--csv", type=str, help="Csv output file")


def main():
    args = argparser.parse_args()
    set_up_db(args.config)

    try:
        campaigns: Campaign = Campaign.objects.get(slug=args.campaign_slug)
    except DoesNotExist:
        ValueError("Cannot find campaign with slug %s" % args.campaign_slug)

    # TODO


if __name__ == "__main__":
    main()
