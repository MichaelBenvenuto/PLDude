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

    def GetDeviceNoPackage(self):
        device = str(self.GetDevice()).upper()
        if device.index("EP") == 0:
            if device[2] == 'M':
                return "EPM"
            elif device[4] == 'E':
                return device[0:][:5]
            else:
                return device[0:][:6]
        elif device[0] == '5':
            if device[2] == 'E':
                return device[0:][:3]
            else:
                return device[0:][:4]
        elif device.index("10") == 0:
            if device[2] == 'M':
                return "10M"
            if device[2] == 'C':
                return device[0:][:3]


    def Run(self, files, program, only_program, verbose):
        altera(files, self, program, only_program, verbose)

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
    elif device[0] == '5':
        if device[1] == 'C':
            return "Cyclone V"
        elif device[1] == 'M':
            return "MAX V"
    elif device.index("10") == 0:
        if device[2] == 'C':
            return "Cyclone 10"
        elif device[2] == 'M':
            return "MAX 10"
    else:
        print("Unknown device " + device + "!")
        exit(-6)

def altera(files, bcon : BuildConfig, program : bool, only_program : bool, verbose : bool):
    if not os.path.exists("./gen/altera"):
        os.makedirs("./gen/altera")

    if not os.path.exists("./gen/altera/logs"):
        os.makedirs("./gen/altera/logs")

    if not (program and only_program):
        qsf_file = open("./gen/altera/project.qsf", "w+")

        print("Generating QSF file from pldprj.yml and pldpin.yml...")
        qsf_file.write("set_global_assignment -name FAMILY \"" + GetFamily(bcon.GetDevice()).upper() + "\"\n")
        qsf_file.write("set_global_assignment -name DEVICE " + bcon.GetDevice() + "\n")
        qsf_file.write("set_global_assignment -name TOP_LEVEL_ENTITY " + bcon.GetTopMod() + "\n")

        for i in files:
            qsf_file.write("set_global_assignment -name " + str(bcon.GetFileType()).upper() + "_FILE ../../" + str(i).replace('\\', '/') + "\n")

        pins = bcon.GetPins()

        for i in pins:
            qsf_file.write("set_location_assignment PIN_" + str(pins[i]) + " -to " + str(i) + "\n")

        qsf_file.close()

        qmap_proc_out = subprocess.PIPE
        if not verbose:
            qmap_proc_out = open("./gen/altera/logs/qmap.log", "w+")

        print("Executing quartus_map (Analysis/synthesis)...")
        qmap_proc = subprocess.Popen(
            ['quartus_map', 'project'],
            cwd="./gen/altera",
            stdout=qmap_proc_out
        )
        process_handler(qmap_proc)

        qfit_proc_out = subprocess.PIPE
        if not verbose:
            qmap_proc_out.close()
            qfit_proc_out = open("./gen/altera/logs/qfit.log", "w+")

        print("Executing quartus_fit...")
        qfit_proc = subprocess.Popen(
            ['quartus_fit', 'project'],
            cwd="./gen/altera",
            stdout=qfit_proc_out
        )
        process_handler(qfit_proc)

        qasm_proc_out = subprocess.PIPE
        if not verbose:
            qfit_proc_out.close()
            qasm_proc_out = open("./gen/altera/logs/qfit.log", "w+")

        print("Executing quartus_asm...")
        qasm_proc = subprocess.Popen(
            ['quartus_asm', 'project'],
            cwd="./gen/altera",
            stdout=qasm_proc_out
        )
        process_handler(qasm_proc)

        if not os.path.exists("./gen/altera/bitfile"):
            os.makedirs("./gen/altera/bitfile")

        if os.path.exists("./gen/altera/bitfile/project.sof"):
            os.remove("./gen/altera/bitfile/project.sof")

        os.rename("./gen/altera/project.sof", "./gen/altera/bitfile/project.sof")

    if program:
        altera_program(verbose)

def altera_program(verbose : bool):

    qpgm_proc_out = subprocess.PIPE
    if not verbose:
        qpgm_proc_out = open("./gen/altera/logs/qpgm.log", "w+")

    qpgm_proc = subprocess.Popen(
        ['quartus_pgm', '-m', 'JTAG', '-o', 'p;./gen/altera/bitfile/project.sof'],
        stdout=qpgm_proc_out,
        stderr=qpgm_proc_out
    )

    qpgm_proc.wait()
    return_code = qpgm_proc.poll()
    if return_code is not None and return_code != 0:
        print("Device was not found by JTAG!")
        exit(-7)

    qpgm_proc_out.close()