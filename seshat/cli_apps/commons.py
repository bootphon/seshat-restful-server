import argparse
from argparse import ArgumentDefaultsHelpFormatter

from seshat.configs import get_config, config_mapping

argparser = argparse.ArgumentParser(formatter_class=ArgumentDefaultsHelpFormatter)
argparser.add_argument("--config", default=get_config(), type=str,
                       choices=list(config_mapping.keys()),
                       help="db name or address")
