#!/usr/bin/env python

import argparse

from slugify import slugify

def get_download_links(campaign_name: str,
                       username: str,
                       password: str,
                       output: str='download_annotations.sh'):
    """ Write download link to requested campaign in bash script"""

    # get campaign id
    campaign_slug = slugify(campaign_name)

    # To get the archives via wget you first need the cookies...
    cookies = ('wget --save-cookies cookies.txt \\'
               '--keep-session-cookies \\'
               '--post-data "username={user}&password={pwd}" \\'
               '--delete-after http://seshat.hadware.ovh/'.format(user=username,
                                                                  pwd=password))

    # now generate download link, beware not to put slash at the end
    # otherwise it downloads the index page.
    download_link = ('wget --load-cookies cookies.txt \\'
                     'http://seshat.hadware.ovh/download/campaign/'
                     '{id}/full_annots_archive '
                     '-O {id}.zip'.format(id=campaign_slug))

    with open(output, 'w') as fout:
        # write download links for 1 campaign. For multiple campaigns,
        # obviously need to download cookies only once.
        fout.write(u'{}\n'.format(cookies))
        fout.write(u'{}\n'.format(download_link))

        # delete cookies at the end
        fout.write(u'rm cookies.txt\n')

def main():
    argparser = argparse.ArgumentParser()
    argparser.add_argument("campaign", type=str,
                           help="Name of the campaign you want to download")

    argparser.add_argument("username", type=str,
                           help="Username of created user")
    argparser.add_argument("password", type=str,
                           help="Password of created user")
    argparser.add_argument("--output", default="download_annotations.sh",
                           type=str, help="name of the outputed bash script")
    args = argparser.parse_args()
    get_download_links(campaign_name=args.campaign,
                       username=args.username,
                       password=args.password,
                       output=args.output)


if __name__ == "__main__":
    main()
