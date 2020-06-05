import os
import subprocess

from BuildConfig import BuildConfig
from BuildConfig import process_handler

from sys import exit

class XstBuild(BuildConfig):
    def GetOptMode(self):
        if not 'optimize' in self.config_stream:
            return "SPEED"
        opt = self.config_stream['optimize'].lower()
        if opt is not any(["speed", "area"]):
            return opt.upper()
        else:
            print("Unknown optimization config: " + str(opt))
            exit(2)

    def GetOptLevel(self):
        if not 'opt-level' in self.config_stream:
            return 1

        olvl = self.config_stream['opt-level']
        if olvl == 0:
            return 1
        elif olvl == 1:
            return 2

    def GetPins(self):
        if not 'xst' in self.pin_stream:
            print("No pin configuration found for XST!")
            exit(-5)
        return self.pin_stream['xst']

def xst(files, bcon : BuildConfig):
    if not os.path.exists("./gen/xilinx"):
        os.makedirs("./gen/xilinx")
    prj_file = open("./gen/xilinx/project.prj", "w+")
    xst_file = open("./gen/xilinx/xst.scr", "w+")

    print("Writing XST script...")
    xst_file.write("run\n-ifn ./project.prj\n")
    xst_file.write("-p " + bcon.GetDevice() + "\n")
    xst_file.write("-top " + bcon.GetTopMod() + "\n")
    xst_file.write("-ifmt " + bcon.GetFileType() + "\n")
    xst_file.write("-opt_mode " + bcon.GetOptMode() + "\n")
    xst_file.write("-opt_level " + str(bcon.GetOptLevel()) + "\n")
    xst_file.write("-ofn ./project.ngc\n")
    xst_file.write("-ofmt ngc")

    print("Writing project files to main file...")

    for i in files:
        prj_str = "work ../../" + i + '\n'
        if bcon.GetFileType().lower() is "Mixed":
            if os.extsep(i)[1].lower() is ".vhd":
                prj_str = "VHDL " + prj_str
            elif os.extsep(i)[1].lower() is ".v":
                prj_str = "verilog " + prj_str
        prj_file.write(prj_str)
    prj_file.close()
    xst_file.close()

    print("Executing XST for synthesis...")
    xst_proc = subprocess.Popen(
        ['xst', '-ifn ./xst.scr', '-ofn ./project_result.srp', '-intstyle silent'],
        cwd=r'./gen/xilinx',
        stdout=subprocess.PIPE)

    process_handler(xst_proc)

    print("XST has finished...")
    print("Generating UCF file from pldpin.yml...")

    ucf_file = open("./gen/xilinx/project.ucf", "w+")

    pins = bcon.GetPins()
    for i in pins:
        ucf_file.write("NET \"" + str(i) + "\" LOC=\"" + str(pins[i]) + "\";\n")
    ucf_file.close()
    print("UCF file generated...")

    print("Executing NGDBuild...")
    ngd_proc = subprocess.Popen(
        ['ngdbuild', '-p', bcon.GetDevice(), '-uc ./project.ucf', './project.ngc', './project.ngd', '-intstyle silent'],
        cwd=r'./gen/xilinx',
        stdout=subprocess.PIPE
    )
    process_handler(ngd_proc)

    print("Executing MAP...")
    map_proc = subprocess.Popen(
        ['map', '-w', '-intstyle silent', '-detail', '-pr b', '-p', bcon.GetDevice(), './project.ngd'],
        cwd=r'./gen/xilinx',
        stdout=subprocess.PIPE
    )
    process_handler(map_proc)

    print("Executing PAR...")
    par_proc = subprocess.Popen(
        ['par', '-w', '-p', '-intstyle silent', './project.ncd', './project_par.ncd', './project.pcf'],
        cwd=r'./gen/xilinx',
        stdout=subprocess.PIPE
    )
    process_handler(par_proc)

    print("Generating bitfile...")

    if not os.path.exists("./gen/xilinx/bitfile"):
        os.makedirs("./gen/xilinx/bitfile")

    bit_proc = subprocess.Popen(
        ['bitgen', '-w', '-g CRC:Enable', '-intstyle silent', './project_par.ncd', './bitfile/project.bit', './project.pcf'],
        cwd=r'./gen/xilinx',
        stdout=subprocess.PIPE
    )
    process_handler(bit_proc)

