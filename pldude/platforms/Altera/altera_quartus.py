import sys
import os
import shutil
import subprocess
import argparse
import logging
import re

from typing import List

from pldude.toolchain import builder

class Quartus(builder):
    @staticmethod
    def setup_args(arguments: dict):
        print(arguments)

    @staticmethod
    def configure_args(parser: argparse.ArgumentParser):
        parser.add_argument('--foo')
        parser.add_argument('--bar')

    @staticmethod
    def check_device(device : str) -> bool:
        print('Quartus')
        return False

    def platform(args: List[str]):
        print(args)

    def synthesize(self):
        print('synthesize')

    def placer(self):
        print('placer')

    def implementer(self):
        print('implement')

    def bitstream(self):
        print('bitstream')