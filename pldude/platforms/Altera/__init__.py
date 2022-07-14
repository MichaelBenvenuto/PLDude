from pldude.platforms.Xilinx7 import PLDUDE_PLATFORM_CLASS
from pldude.bconfigs import BuildConfig
from .altera_quartus import Altera

PLDUDE_PLATFORM_CLASS : BuildConfig = Altera