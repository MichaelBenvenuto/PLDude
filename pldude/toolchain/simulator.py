from .tool import tool
from abc import abstractmethod

class simulator(tool):
    @abstractmethod
    def simulate(self):
        pass