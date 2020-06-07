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

    def GetDeviceNoPackage(self):
        dev = str(self.GetDevice())
        return dev.split('-')[0]

    def Run(self, files, program, only_program, verbose):
        xst(files, self, program, only_program, verbose)


def xst(files, bcon : BuildConfig, program : bool, only_program : bool, verbose : bool):
    if not os.path.exists("./gen/xilinx"):
        os.makedirs("./gen/xilinx")

    if not (program and only_program):
        if not os.path.exists("./gen/xilinx/logs"):
            os.makedirs("./gen/xilinx/logs")

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

        xst_proc_out = subprocess.PIPE
        if not verbose:
            xst_proc_out = open("./gen/xilinx/logs/xst.log", "w+")

        print("Executing XST for synthesis...")
        xst_proc = subprocess.Popen(
            ['xst', '-ifn ./xst.scr', '-ofn ./project_result.srp', '-intstyle ise'],
            cwd=r'./gen/xilinx',
            stdout=xst_proc_out
        )
        process_handler(xst_proc)
        ngd_proc_out = subprocess.PIPE
        if not verbose:
            ngd_proc_out = open("./gen/xilinx/logs/ngd.log", "w+")
            xst_proc_out.close()
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
            ['ngdbuild', '-p', bcon.GetDevice(), '-uc ./project.ucf', './project.ngc', './project.ngd', '-intstyle ise'],
            cwd=r'./gen/xilinx',
            stdout=ngd_proc_out
        )
        process_handler(ngd_proc)
        map_proc_out = subprocess.PIPE
        if not verbose:
            map_proc_out = open("./gen/xilinx/logs/map.log", "w+")
            ngd_proc_out.close()

        print("Executing MAP...")
        map_proc = subprocess.Popen(
            ['map', '-w', '-intstyle silent', '-detail', '-pr b', '-p', bcon.GetDevice(), './project.ngd'],
            cwd=r'./gen/xilinx',
            stdout=map_proc_out
        )
        process_handler(map_proc)
        par_proc_out = subprocess.PIPE
        if not verbose:
            map_proc_out.close()
            par_proc_out = open("./gen/xilinx/logs/par.log", "w+")

        print("Executing PAR...")
        par_proc = subprocess.Popen(
            ['par', '-w', '-p', '-intstyle ise', './project.ncd', './project_par.ncd', './project.pcf'],
            cwd=r'./gen/xilinx',
            stdout=par_proc_out
        )
        process_handler(par_proc)
        bit_proc_out = subprocess.PIPE
        if not verbose:
            bit_proc_out = open("./gen/xilinx/logs/bit.log", "w+")

        print("Generating bitfile...")
        if not os.path.exists("./gen/xilinx/bitfile"):
            os.makedirs("./gen/xilinx/bitfile")

        bit_proc = subprocess.Popen(
            ['bitgen', '-w', '-g CRC:Enable', '-intstyle ise', './project_par.ncd', './bitfile/project.bit', './project.pcf'],
            cwd=r'./gen/xilinx',
            stdout=bit_proc_out
        )
        process_handler(bit_proc)

        if not verbose:
            bit_proc_out.close()

    if program:
        xst_program(verbose)

def xst_program(verbose : bool):

    cmd_file = open("./gen/xilinx/project.cmd", "w+")
    cmd_file.write("setMode -bscan\n")
    cmd_file.write("setCable -p auto\n")
    cmd_file.write("addDevice -p 1 -file ./bitfile/project.bit\n")
    cmd_file.write("program -p 1\n")
    cmd_file.write("quit\n")
    cmd_file.close()

    impact_proc_out = subprocess.PIPE
    if not verbose:
        impact_proc_out = open("./gen/xilinx/logs/impact.log", "w+")
    impact_proc = subprocess.Popen(
        ['impact', '-batch', './project.cmd'],
        cwd=r'./gen/xilinx',
        stdout=impact_proc_out,
        stderr=impact_proc_out
    )

    impact_proc.wait()
    return_code = impact_proc.poll()
    if return_code is not None and return_code != 0:
        print("Device was not found by JTAG!")
        exit(-7)

    if not verbose:
        impact_proc_out.close()

