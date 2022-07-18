import argparse
from typing import List

from pldude.toolchain import builder

class Vivado(builder):
    @staticmethod
    def setup(arguments: dict):
        print(arguments)

    @staticmethod
    def configure_args(parser: argparse.ArgumentParser):
        parser.add_argument('--test')
        parser.add_argument('--tester')

    @staticmethod
    def check_device(device : str) -> bool:
        print('Vivado')
        return True

    def platform(args: List):
        print(args)

    def synthesize(self):
        print('synthesize')

    def placer(self):
        print('placer')

    def implementer(self):
        print('implement')

    def bitstream(self):
        print('bitstream')