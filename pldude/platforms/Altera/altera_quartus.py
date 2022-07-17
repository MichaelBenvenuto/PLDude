import sys
import os
import shutil
import subprocess
import argparse
import logging
import re

from typing import Union, IO

from pldude.toolchain import builder

class Quartus(builder):
    @staticmethod
    def setup_args(arguments: dict):
        print(arguments)

    @staticmethod
    def configure_args(parser: argparse.ArgumentParser):
        parser.add_argument('--foo')
        parser.add_argument('--bar')