import argparse
from seshat.configs import get_config

argparser = argparse.ArgumentParser()
argparser.add_argument("--config", default=get_config(), type=get_config,
                       help="db name or address")
