from mongoengine import connect, DoesNotExist

from seshat.models import Campaign, Annotator, SingleAnnotatorTask, DoubleAnnotatorTask, BaseTask
from .commons import argparser

argparser.add_argument("campaign_slug", type=str, help="Campaign slug for which the task are assigned")
argparser.add_argument("--files", type=str, nargs="*", help="List of files to assign")
group = argparser.add_mutually_exclusive_group("task_type", required=True)
group.add_argument("--single", action="store_true")
group.add_argument("--double", action="store_true")
single_group = group.add_argument_group("single annotator task group")
single_group.add_argument("--annotator", type=str)
double_group = group.add_argument_group("double annotators task group")
single_group.add_argument("--target", type=str)
single_group.add_argument("--reference", type=str)

# TODO : add "assign as user" parameter, and better document how the files have to be listed

def main():
    args = argparser.parse_args()
    connect(args.db)
    try:
        campaign: Campaign = Campaign.objects.get(slug=args.campaign_slug)
    except DoesNotExist:
        raise ValueError("Cannot find campaign with slug %s" % args.campaign_slug)

    if args.task_type.single:
        annotator = Annotator.objects.get(username=args["single_annot_assign"]["annotator"])
        task_class = SingleAnnotatorTask
        annotators = {"annotator": annotator}
    else:
        reference = Annotator.objects.get(username=args["double_annot_assign"]["reference"])
        target = Annotator.objects.get(username=args["double_annot_assign"]["target"])
        task_class = DoubleAnnotatorTask
        annotators = {"reference": reference,
                      "target": target}

    for file in args.files:
        new_task: BaseTask = task_class(**annotators)
        template_doc = campaign.gen_template_tg(file)
        template_doc.creators = []
        template_doc.save()
        new_task.template_tg = template_doc
        new_task.campaign = campaign
        new_task.data_file = file
        new_task.assigner = campaign.creator
        new_task.save()
        template_doc.task = new_task
        template_doc.save()
        campaign.tasks.append(new_task)
        for user in annotators.values():
            user.assigned_tasks.append(new_task)
    task_class.notify_assign(list(annotators.values()), campaign)
    campaign.save()


if __name__ == "__main__":
    main()
