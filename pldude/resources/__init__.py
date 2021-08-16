import os
import io
import pkgutil

class ResourceManager():
    def GetResource(self, resource : str) -> io.TextIOWrapper:
        return open(self.GetResourceDir(resource))

    def GetResourceDir(self, resource : str) -> str:
        return os.path.abspath(os.path.dirname(__file__) + "/" + self.__class__.__name__ + "/" + resource)