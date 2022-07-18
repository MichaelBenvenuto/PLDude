from .tool import tool
from abc import abstractmethod

class builder(tool):
    @abstractmethod
    def synthesize(self):
        pass

    @abstractmethod
    def placer(self):
        pass

    @abstractmethod
    def implementer(self):
        pass

    @abstractmethod
    def bitstream(self):
        pass