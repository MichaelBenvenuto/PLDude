from os import listdir
from os.path import splitext

import yaml
from BuildConfig import BuildConfig

from build_xst import xst
# from build_xst import XstBuild

try:
    config_file = open(r"./pldprj.yml", "r")
except FileNotFoundError:
    print("pldprj.yml was not found, creating file...")
    config_file = open(r"./pldprj.yml", "w+")

config_stream = yaml.full_load(config_file)

# Need a better way of updating config files with new information...
if config_stream is None:
    config_stream = dict()
    config_stream['filetype'] = None
    config_stream['device'] = None
    config_stream['top'] = None
    config_stream['optimize'] = None
    config_stream['opt-level'] = 0
    yaml.dump(config_stream, config_file)
    config_file.close()
    print("Wrote default data to pldprj.yml...")
    exit(0)

# Need a way of making a static function in BuildConfig to detect if a device is Xilinx, Altera, Lattice, etc.
# Possibly a hash function?
# Not using a NN, i know this is python, but not everything needs AI...
bcon = BuildConfig(config_stream)

files = []

for i in listdir("./"):
    ext = splitext(i)[1]
    if (ext == ".vhd" and bcon.file_type.lower() == "vhdl") or (ext == ".v" and bcon.file_type.lower() == "verilog"):
        files.append(i)

xst(files, bcon)

config_stream['filetype'] = bcon.file_type
config_stream['device'] = bcon.device
config_stream['top'] = bcon.top
config_stream['optimize'] = bcon.opt

config_file = open(r"./pldprj.yml", "w+")
yaml.dump(config_stream, config_file, sort_keys=False)
config_file.close()