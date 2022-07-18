import os
import sys
import pkgutil
import importlib

from typing import Dict, List
from types import ModuleType

from pldude.toolchain import tool
from pldude.toolchain.builder import builder
from pldude.toolchain.simulator import simulator
from pldude.utils.error import PLDudeError

class _PlatformEntry():
    name : str
    tool : tool
    tool_resources : str

    def __init__(self, dir : str):
        self.tool_resources = dir

class Platforms():
    simulators : List[_PlatformEntry] = []
    builders : List[_PlatformEntry] = []
    
    simulators_dict : Dict[str, simulator] = {}
    builders_dict : Dict[str, builder] = {}

    __PLATFORM_REQ_VARS = ['PLDUDE_PLATFORM_BUILDER', 'PLDUDE_PLATFORM_SIMULATOR']

    @staticmethod
    def load_platforms(plugin : ModuleType) -> None:
        plugins = pkgutil.iter_modules(plugin.__path__, f'{plugin.__name__}.')
        modules = Platforms
        for finder, name, ispkg in plugins:
            module = importlib.import_module(name)
            if all(j in dir(module) for j in modules.__PLATFORM_REQ_VARS):
                if module.PLDUDE_PLATFORM_BUILDER != None:
                    resource = _PlatformEntry(f'{os.path.dirname(sys.modules[name].__file__)}/resources')
                    resource.tool = module.PLDUDE_PLATFORM_BUILDER
                    resource.name = resource.tool.__name__
                    modules.builders.append(resource)

                    if modules.builders_dict.get(resource.name, None) == None:
                        modules.builders_dict.update({resource.name: resource.tool})
                    else:
                        raise PLDudeError(f'Duplicate module \'{resource.name}\'')

                if module.PLDUDE_PLATFORM_SIMULATOR != None:
                    resource = _PlatformEntry(f'{os.path.dirname(sys.modules[name].__file__)}/resources')
                    resource.tool = module.PLDUDE_PLATFORM_BUILDER
                    resource.name = resource.tool.__name__
                    modules.simulators.append(resource)

                    if modules.simulators_dict.get(resource.name, None) == None:
                        modules.simulators_dict.update({resource.name: resource.tool})
                    else:
                        raise PLDudeError(f'Duplicate module \'{resource.name}\'')