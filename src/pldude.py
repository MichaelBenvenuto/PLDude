import glob
from os.path import splitext

import yaml
from BuildConfig import BuildConfig

from build_xst import xst
from build_xst import XstBuild

from build_altera import altera
from build_altera import AlteraBuild

from sys import exit

system = 0

config_file = 0
pin_file = 0

print("PLDude v0.1")
print("-----------")

try:
    config_file = open(r"./pldprj.yml", "r")
except FileNotFoundError:
    print("pldprj.yml was not found!")
    exit(-1)

try:
    pin_file = open(r"./pldpin.yml", "r")
except FileNotFoundError:
    print("pldpin.yml was not found!")
    exit(-1)

config_stream = yaml.full_load(config_file)
pin_stream = yaml.full_load(pin_file)

if config_stream is None:
    print("empty pldprj.yml!")
    exit(-2)

if config_stream is None:
    print("empty pldpin.yml!")
    exit(-2)

device = config_stream['device'].lower()

# Need a way of making a static function in BuildConfig to detect if a device is Xilinx, Altera, Lattice, etc.
# Possibly a hash function?
# Not using a NN, i know this is python, but not everything needs AI...
if device[0] == 'x':
    bcon = XstBuild(config_stream, pin_stream)
    system = 0
elif device[0] == 'e' or device[0] == '5' or str(device).index('10') == 0:
    bcon = AlteraBuild(config_stream, pin_stream)
    system = 1
else:
    print("Unknown device!")
    exit(-3)

src_dir = str(config_stream['src'])
mode = str(config_stream['filetype'])

if mode.lower() == "vhdl":
    files = [f for f in glob.glob(src_dir + "**/*.vhd", recursive=True)]
elif mode.lower() == "verilog":
    files = [f for f in glob.glob(src_dir + "**/*.v", recursive=True)]
else:
    files = [f for f in glob.glob(src_dir + "**/*[.v,.vhdl]")]

if system == 0:
    xst(files, bcon)
elif system == 1:
    altera(files, bcon)