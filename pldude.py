import yaml

from BuildConfig import BuildConfig
from build_xst import xst
from os import listdir
from os.path import splitext

try:
    config_file = open(r"./pldprj.yml", "r")
except FileNotFoundError:
    config_file = open(r"./pldprj.yml", "w+")

config_stream = yaml.full_load(config_file)
config_file.close()

if config_stream is None:
    config_stream = dict()
    config_stream['filetype'] = None
    config_stream['device'] = None
    config_stream['top'] = None
    config_stream['optimize'] = None

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