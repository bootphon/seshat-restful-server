import tqdm
from mongoengine import DoesNotExist

from seshat.configs import set_up_db
from seshat.models import Campaign
from seshat.models.tasks import DoubleAnnotatorTask
from .commons import argparser

argparser.add_argument("campaign_slug", type=str, help="Slug for which you want to retrieve the gamma summary")
exclusive_group = argparser.add_mutually_exclusive_group()
compute = exclusive_group.add_argument_group()
compute.add_argument("--csv", type=str, help="Csv output file")
compute.add_argument("-f", "--force", action="store_true",
                       help="Force recomputation of the gamma value")
exclusive_group.add_argument("--clear", action="store_true",
                             help="Clear the computed gamma values for that campaign")


def main():
    args = argparser.parse_args()
    set_up_db(args.config)

    try:
        campaign: Campaign = Campaign.objects.get(slug=args.campaign_slug)
    except DoesNotExist:
        print("Cannot find campaign with slug %s" % args.campaign_slug)
        exit(1)

    if args.clear:
        for task in campaign.tasks:
            if isinstance(task, DoubleAnnotatorTask):
                task.tiers_gamma = None
                task.save()
        campaign.stats.tiers_gamma = None
        campaign.update_stats()
        print("Cleared all gamma values")
        exit()


    if not campaign.stats.can_compute_gamma:
        print(f"It's not possible to compute the gamma agreement for campaign"
              f" {campaign.name}")
        exit(1)

    for task in tqdm.tqdm(campaign.tasks):
        if not isinstance(task, DoubleAnnotatorTask):
            continue

        if task.merged_tg is None:
            print(f"Ref or target textgrids not yet completed for task on file "
                  f"{task.data_file}, skipping.")
            continue

        if task.tiers_gamma and not args.force:
            print(f"No need to compute gamma for task on file "
                  f"{task.data_file}, skipping.")
            continue

        task.compute_gamma()
        task.save()

    print("Gamma computation is done.")
    campaign.stats.gamma_updating = False
    campaign.update_stats(gamma_only=True)
    print("Gamma values:")
    for tier_name, gamma_value in campaign.stats.tiers_gamma.items():
        print(f"{tier_name} : {gamma_value}")


if __name__ == "__main__":
    main()
