from itertools import chain
from pathlib import Path

from seshat.configs import set_up_db
from ..models import SingleAnnotatorTextGrid, Campaign
from ..models.errors import error_log
from .commons import argparser

argparser.add_argument("campaign", type=str,
                       help="Campaign for which the textgrid should be checked")
argparser.add_argument("textgrid_path", type=Path, nargs="+",
                       help="Textgrid(s) path(s) that is to be checked (if only one). "
                            "Two textgrids must be specified to be tested for merge")
argparser.add_argument("--step", type=str, choices=["annots", "merge_annots", "merge_times"], default="annots",
                       help="Step for which to check the textgrids")
argparser.add_argument("--merge", action="store_true",
                       help="Test a textgrid couple for mergeability.")


# TODO : allow for double annotator tasks checking (annot merge, time merge)

def main():
    args = argparser.parse_args()
    set_up_db(args.config)

    # opening textgrid file as binary
    with open(args.textgrid_path[0], "rb") as tg_file:
        tg_bytes = tg_file.read()

    campaign: Campaign = Campaign.objects.get(slug=args.campaign)

    # creating a "fake" Textgrid document
    tg_doc = SingleAnnotatorTextGrid(textgrid_file=tg_bytes, checking_scheme=campaign.checking_scheme)
    error_log.flush()
    tg_doc.check()

    if error_log.has_errors:
        if error_log.structural:
            print(f"-> Structural Errors ({len(error_log.structural)}):")
            for error in error_log.structural:
                print(f"\t* {error.msg}")

        if error_log.annot:
            print(f"-> Annotation Errors ({len(list(chain.from_iterable(error_log.annot.values())))})")
            for tier, errors in error_log.annot.items():
                print(f"\t- In tier '{tier}'")
                for error in errors:
                    print(f"\t\t* In interval {error.annot_idx}: {error.msg}")
    else:
        print("✓ No errors. Textgrid is valid")


if __name__ == "__main__":
    main()
