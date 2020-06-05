import os
import subprocess

from BuildConfig import BuildConfig
from BuildConfig import process_handler

from sys import exit

class AlteraBuild(BuildConfig):
    def GetOptMode(self):
        if not 'optimize' in self.config_stream:
            return "speed"
        opt = self.config_stream['optimize'].lower()
        if opt is not any(["speed", "area"]):
            return opt
        else:
            print("Unknown optimization config: " + str(opt))
            exit(2)

    def GetPins(self):
        if not 'altera' in self.pin_stream:
            print("No pin configuration found for Altera!")
            exit(-5)
        return self.pin_stream['altera']

# Intel claims that quartus_map "automatically" detects the device family based on the part...
# What a croc of sh*t...
# This is only based of of quartus lite
def GetFamily(device : str):
    if device.index("EP") == 0:
        if device[3] == 'C':
            return "Cyclone IV"
        elif device[2] == 'M':
            return "MAX II"
        elif device[3] == 'A':
            return "Arria II"
    elif device.index("5M") == 0:
        return "MAX V"
    elif device[0] == '5':
        if device[1] == 'C':
            return "Cyclone V"
    elif device.index("10") == 0:
        if device[2] == 'C':
            return "Cyclone 10"
        elif device[2] == 'M':
            return "MAX 10"
    else:
        print("Unknown device " + device + "!")

def altera(files, bcon : BuildConfig):
    if not os.path.exists("./gen/altera"):
        os.makedirs("./gen/altera")
    qsf_file = open("./gen/altera/project.qsf", "w+")

    print("Generating QSF file from pldprj.yml and pldpin.yml...")
    qsf_file.write("set_global_assignment -name FAMILY \"" + GetFamily(bcon.GetDevice()) + "\"\n")
    qsf_file.write("set_global_assignment -name DEVICE " + bcon.GetDevice() + "\n")
    qsf_file.write("set_global_assignment -name TOP_LEVEL_ENTITY " + bcon.GetTopMod() + "\n")

    for i in files:
        qsf_file.write("set_global_assignment -name " + str(bcon.GetFileType()).upper() + "_FILE ../../" + str(i).replace('\\', '/') + "\n")

    pins = bcon.GetPins()

    for i in pins:
        qsf_file.write("set_location_assignment PIN_" + str(pins[i]) + " -to " + str(i) + "\n")

    qsf_file.close()

    print("Executing quartus_map (Analysis/synthesis)...")
    qmap_proc = subprocess.Popen(
        ['quartus_map', 'project'],
        cwd="./gen/altera",
        stdout=subprocess.PIPE
    )
    process_handler(qmap_proc)

    print("Executing quartus_fit...")
    qfit_proc = subprocess.Popen(
        ['quartus_fit', 'project'],
        cwd="./gen/altera",
        stdout=subprocess.PIPE
    )
    process_handler(qfit_proc)

    print("Executing quartus_asm...")
    qasm_proc = subprocess.Popen(
        ['quartus_asm', 'project'],
        cwd="./gen/altera",
        stdout=subprocess.PIPE
    )
    process_handler(qasm_proc)

    if not os.path.exists("./gen/altera/bitfile"):
        os.makedirs("./gen/altera/bitfile")

    os.rename("./gen/altera/project.sof", "./gen/altera/bitfile/project.sof")