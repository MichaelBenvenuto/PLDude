from pldude.toolchain import builder, simulator
from .x7 import Vivado

PLDUDE_PLATFORM_BUILDER : builder = Vivado
PLDUDE_PLATFORM_SIMULATOR : simulator = None