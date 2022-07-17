import os
import sys
import pkgutil
import importlib

from typing import List, Dict
from types import ModuleType

from pldude.toolchain import tool

__PLATFORM_REQ_VARS = ['PLDUDE_PLATFORM_BUILDER', 'PLDUDE_PLATFORM_SIMULATOR']

class _PlatformEntry():
    def __init__(self, dir : str):
        self.tool_resources = dir

    name : str
    tool : tool
    tool_resources : str

def get_platforms(plugin : ModuleType) -> Dict[str, List[_PlatformEntry]]:
    plugins = pkgutil.iter_modules(plugin.__path__, f'{plugin.__name__}.')
    modules = {
        'simulators': [],
        'builders': []
    }
    for finder, name, ispkg in plugins:
        module = importlib.import_module(name)
        if all(j in dir(module) for j in __PLATFORM_REQ_VARS):
            if module.PLDUDE_PLATFORM_BUILDER != None:
                resource = _PlatformEntry(f'{os.path.dirname(sys.modules[name].__file__)}/resources')
                resource.tool = module.PLDUDE_PLATFORM_BUILDER
                resource.name = resource.tool.__name__
                modules['builders'].append(resource)

            if module.PLDUDE_PLATFORM_SIMULATOR != None:
                resource = _PlatformEntry(f'{os.path.dirname(sys.modules[name].__file__)}/resources')
                resource.tool = module.PLDUDE_PLATFORM_BUILDER
                resource.name = resource.tool.__name__
                modules['simulators'].append(resource)
    return modules