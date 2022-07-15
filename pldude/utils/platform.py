from abc import abstractmethod, ABC


class Platform(ABC):
    @abstractmethod
    def ListDevices(self, argv):
        pass
