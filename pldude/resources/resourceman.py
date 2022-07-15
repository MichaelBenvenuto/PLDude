import os
import io

class ResourceManager():
    resource_dir = '.'
    def GetResource(self, resource : str) -> io.TextIOWrapper:
        return open(self.GetResourceDir(resource))

    def GetResourceDir(self, resource : str) -> str:
        return os.path.abspath(f"{self.resource_dir}/{resource}")