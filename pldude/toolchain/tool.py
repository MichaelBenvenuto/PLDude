import argparse

from abc import ABC, abstractmethod


class tool(ABC):
    @staticmethod
    @abstractmethod
    def setup_args(arguments: dict):
        pass

    @staticmethod
    @abstractmethod
    def configure_args(parser : argparse.ArgumentParser):
        pass