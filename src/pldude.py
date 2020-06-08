import glob
import os
from sys import argv

import yaml
from BuildConfig import BuildConfig

from build_xst import XstBuild
from build_altera import AlteraBuild

from sys import exit

system = 0

config_file = 0
pin_file = 0

print("PLDude v0.2")
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

if not 'device' in config_stream:
    print("No device specified!")
    exit(-2)

device = config_stream['device'].lower()

# Need a way of making a static function in BuildConfig to detect if a device is Xilinx, Altera, Lattice, etc.
# Possibly a hash function?
# Not using a NN, i know this is python, but not everything needs AI...
bcon = BuildConfig(config_stream, pin_stream)
if device[0] == 'x':
    bcon = XstBuild(config_stream, pin_stream)
elif device[0] == 'e' or device[0] == '5' or str(device).index('10') == 0:
    bcon = AlteraBuild(config_stream, pin_stream)
else:
    print("Unknown device!")
    exit(-3)

src_dir = bcon.GetSrcDir()
mode = bcon.GetFileType()

files = []

glob_ext = "/*"

if mode.lower() == "vhdl":
    files = [f for f in glob.glob(src_dir + "/**/*.vhd", recursive=True)
             if not str(os.path.dirname(f)).replace("\\", "/").startswith(src_dir + "/" + bcon.GetDeviceDir())]
    glob_ext = "/*.vhd"
elif mode.lower() == "verilog":
    files = [f for f in glob.glob(src_dir + "/**/*.v", recursive=True)
             if not str(os.path.dirname(f)).replace("\\", "/").startswith(src_dir + "/" + bcon.GetDeviceDir())]
    glob_ext = "/*.v"
elif mode.lower() == "mixed":
    files = [f for f in glob.glob(src_dir + "/**/*[.v,.vhd]", recursive=True)
             if not str(os.path.dirname(f)).replace("\\", "/").startswith(src_dir + "/" + bcon.GetDeviceDir())]
    glob_ext = "/*[.v, .vhd]"
else:
    print("Unknown mode: " + mode)
    exit(-4)

files.extend(glob.glob(src_dir + "/" + bcon.GetDeviceDir() + "/" + bcon.GetDeviceNoPackage() + glob_ext))

program = '-p' in argv or '-po' in argv
program_only = '-po' in argv
verbose = '-v' in argv

bcon.Run(files, program, program_only, verbose)