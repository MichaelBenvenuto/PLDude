import argparse

from pldude.toolchain import builder

class Vivado(builder):
    @staticmethod
    def setup_args(arguments: dict):
        print(arguments)

    @staticmethod
    def configure_args(parser: argparse.ArgumentParser):
        parser.add_argument('--test')
        parser.add_argument('--tester')