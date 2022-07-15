import os
import sys
import importlib
import pkgutil

from types import ModuleType

class PlatformManager():

    PLATFORM_REQ_VARS = ['PLDUDE_PLATFORM_CLASS']

    def __init__(self, plugin : ModuleType) -> ModuleType:
        plugins = pkgutil.iter_modules(plugin.__path__, f"{plugin.__name__}.")
        modules = [(importlib.import_module(name),f"{os.path.dirname(sys.modules[name].__file__)}/resources") for finder, name, ispkg in plugins]
        self.platform_classes = []
        for i in modules:
            # Use all for future use cases
            if all(j in dir(i[0]) for j in self.PLATFORM_REQ_VARS):
                self.platform_classes.append(i)