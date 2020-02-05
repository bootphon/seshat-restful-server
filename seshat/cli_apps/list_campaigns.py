from seshat.configs import set_up_db
from .commons import argparser
from ..models import Campaign, BaseTask

argparser.add_argument("--show_tasks", action="store_true", help="Also list tasks for the campaigns")


def main():
    args = argparser.parse_args()
    set_up_db(args.config)

    print(f"Found {Campaign.objects.count()} campaigns in database {Campaign._get_db().name}")
    for campaign in Campaign.objects:
        campaign: Campaign
        print(f"\t- Campaign \"{campaign.name}\" (slug: {campaign.slug}) : {len(campaign.tasks)} tasks")
        if args.show_tasks:
            for task in campaign.tasks:
                task: BaseTask
                print(f"\t\t* Task on file {task.data_file}, STEP : {task.steps_names[task.current_step]}")


if __name__ == "__main__":
    main()
