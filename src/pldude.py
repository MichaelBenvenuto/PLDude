from os import listdir
from os.path import splitext

import yaml
from BuildConfig import BuildConfig

from build_xst import xst
from build_xst import XstBuild

config_file = 0
pin_file = 0

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
else:
    print("Unknown device!")
    exit(-3)

files = []

for i in listdir("./"):
    ext = splitext(i)[1]
    if (ext == ".vhd" and bcon.GetFileType().lower() == "vhdl") or (ext == ".v" and bcon.GetFileType().lower() == "verilog"):
        files.append(i)

xst(files, bcon)

config_stream['filetype'] = bcon.GetFileType()
config_stream['device'] = bcon.GetDevice()
config_stream['top'] = bcon.GetTopMod()
config_stream['optimize'] = bcon.GetOptMode()

config_file = open(r"./pldprj.yml", "w+")
yaml.dump(config_stream, config_file, sort_keys=False)
config_file.close()