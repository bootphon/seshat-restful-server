from mongoengine import DoesNotExist
import pygamma
from seshat.models.tasks import DoubleAnnotatorTask
import tqdm

from seshat.configs import set_up_db
from seshat.models import Campaign
from .commons import argparser

argparser.add_argument("campaign_slug", type=str, help="Slug for which you want to retrieve the gamma summary")
argparser.add_argument("--csv", type=str, help="Csv output file")


def main():
    args = argparser.parse_args()
    set_up_db(args.config)

    try:
        campaign: Campaign = Campaign.objects.get(slug=args.campaign_slug)
    except DoesNotExist:
        print("Cannot find campaign with slug %s" % args.campaign_slug)
        exit(1)

    if not campaign.stats.can_compute_gamma:
        print(f"It's not possible to compute the gamma agreement for campaign"
              f" {campaign.name}")
        exit(1)

    for task in tqdm.tqdm(campaign.tasks):
        if not isinstance(task, DoubleAnnotatorTask):
            continue

        if task.merged_tg is None:
            print(f"Ref or target textgrids not yet completed for task on file "
                  f"f{task.data_file.name}, skipping.")
            continue

        if task.tiers_gamma:
            print(f"No need to compute gamma for task on file "
                  f"f{task.data_file.name}, skipping.")
            continue

        task.compute_gamma()
        task.save()

    print("Gamma computation is done.")
    campaign.stats.gamma_updating = False
    campaign.update_stats(gamma_only=True)

if __name__ == "__main__":
    main()
