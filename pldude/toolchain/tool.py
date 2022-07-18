import argparse

from abc import ABC, abstractmethod
from typing import List


class tool(ABC):
    @staticmethod
    @abstractmethod
    def setup(arguments: dict):
        pass

    @staticmethod
    @abstractmethod
    def configure_args(parser : argparse.ArgumentParser):
        pass

    @staticmethod
    @abstractmethod
    def check_device(device : str) -> bool:
        pass

    @abstractmethod
    def platform(args : List):
        pass