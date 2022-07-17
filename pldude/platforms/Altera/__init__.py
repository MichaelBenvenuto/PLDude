from pldude.toolchain import builder, simulator
from .altera_quartus import Quartus

PLDUDE_PLATFORM_BUILDER : builder = Quartus
PLDUDE_PLATFORM_SIMULATOR : simulator = None