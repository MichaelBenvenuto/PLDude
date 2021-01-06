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


    def Run(self, files, program, only_program, simulate, simulate_file, verbose):
        if simulate:
            print("Altera simulation not supported yet!")
        else:
            altera(files, self, program, only_program, verbose)

# Intel claims that quartus_map "automatically" detects the device family based on the part...
# What a croc of sh*t...
# This is only based off of quartus lite
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

    if not (program and only_program):
        if not os.path.exists("./gen/altera/logs"):
            os.makedirs("./gen/altera/logs")

        qsf_file = open("./gen/altera/project.qsf", "w+")

        print("Generating QSF file from pldprj.yml and pldpin.yml...")
        qsf_file.write("set_global_assignment -name FAMILY \"" + GetFamily(bcon.GetDevice()).upper() + "\"\n")
        qsf_file.write("set_global_assignment -name DEVICE " + bcon.GetDevice() + "\n")
        qsf_file.write("set_global_assignment -name TOP_LEVEL_ENTITY " + bcon.GetTopMod() + "\n")

        for i in files:
            qsf_file.write("set_global_assignment -name " + str(bcon.GetFileType()).upper() + "_FILE ../../" + str(i).replace('\\', '/') + "\n")

        pins = bcon.GetPins()

        for i in pins:
            pin = pins[i]
            if type(pin) == str:
                qsf_file.write("set_location_assignment PIN_" + str(pin) + " -to " + str(i) + "\n")
            elif type(pin) == dict:
                qsf_file.write("set_instance_assignment -name IOSTANDARD \"" + str(pins['iostd']) + "\" -to " + str(i))
                qsf_file.write("set_location_assignment PIN_" + str(pin['pkg']) + " -to " + str(i) + "\n")

        qsf_file.close()

        qmap_proc_out = open("./gen/altera/logs/qmap.log", "w+")

        print("Executing quartus_map (Analysis/synthesis)...")
        qmap_proc = subprocess.Popen(
            ['quartus_map', 'project'],
            cwd="./gen/altera",
            stdout=subprocess.PIPE
        )
        process_handler(qmap_proc, verbose, qmap_proc_out)
        qmap_proc_out.close()

        qfit_proc_out = open("./gen/altera/logs/qfit.log", "w+")

        print("Executing quartus_fit...")
        qfit_proc = subprocess.Popen(
            ['quartus_fit', 'project'],
            cwd="./gen/altera",
            stdout=subprocess.PIPE
        )
        process_handler(qfit_proc, verbose, qfit_proc_out)
        qfit_proc_out.close()

        qasm_proc_out = open("./gen/altera/logs/qfit.log", "w+")

        print("Executing quartus_asm...")
        qasm_proc = subprocess.Popen(
            ['quartus_asm', 'project'],
            cwd="./gen/altera",
            stdout=subprocess.PIPE
        )
        process_handler(qasm_proc, verbose, qasm_proc_out)
        qasm_proc_out.close()

        if not os.path.exists("./gen/altera/bitfile"):
            os.makedirs("./gen/altera/bitfile")

        if os.path.exists("./gen/altera/bitfile/project.sof"):
            os.remove("./gen/altera/bitfile/project.sof")

        os.rename("./gen/altera/project.sof", "./gen/altera/bitfile/project.sof")

    if program:
        altera_program(verbose)

def altera_program(verbose : bool):

    print("Executing quartus_pgm...")
    qpgm_proc_out = open("./gen/altera/logs/qpgm.log", "w+")

    qpgm_proc = subprocess.Popen(
        ['quartus_pgm', '-m', 'JTAG', '-o', 'p;./gen/altera/bitfile/project.sof'],
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE
    )
    process_handler(qpgm_proc, verbose, qpgm_proc_out)
    qpgm_proc_out.close()

    return_code = qpgm_proc.poll()
    if return_code is not None and return_code != 0:
        print("Device was not found by JTAG!")
        exit(-7)