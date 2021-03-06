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

    def Run(self, files, program, only_program, simulate, simmod, verbose):
        if simulate:
            xst_simulate(files, simmod, self)
        else:
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

        xst_proc_out = open("./gen/xilinx/logs/xst.log", "w+")

        print("Executing XST...")
        xst_proc = subprocess.Popen(
            ['xst', '-ifn ./xst.scr', '-ofn ./project_result.srp', '-intstyle ise'],
            cwd=r'./gen/xilinx',
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT
        )
        process_handler(xst_proc, verbose, xst_proc_out)
        xst_proc_out.close()

        print("Generating UCF file from pldpin.yml...")
        ucf_file = open("./gen/xilinx/project.ucf", "w+")
        pins = bcon.GetPins()
        for i in pins:
            pin = pins[i]
            if type(pin) == str:
                ucf_file.write("NET \"" + str(i) + "\" LOC=\"" + str(pin) + "\";\n")
            elif type(pin) == dict:
                ucf_file.write("NET \"" + str(i) + "\" IOSTANDARD=\"" + str(pin['iostd']) + "\" LOC=\"" + str(pin['pkg']) + "\";\n")
        ucf_file.close()
        print("UCF file generated...")

        ngd_proc_out = open("./gen/xilinx/logs/ngd.log", "w+")
        print("Executing NGDBuild...")
        ngd_proc = subprocess.Popen(
            ['ngdbuild', '-p', bcon.GetDevice(), '-uc ./project.ucf', './project.ngc', './project.ngd', '-intstyle ise'],
            cwd=r'./gen/xilinx',
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT
        )
        process_handler(ngd_proc, verbose, ngd_proc_out)

        map_proc_out = open("./gen/xilinx/logs/map.log", "w+")
        print("Executing MAP...")
        map_proc = subprocess.Popen(
            ['map', '-w', '-intstyle ise', '-detail', '-pr b', '-p', bcon.GetDevice(), './project.ngd'],
            cwd=r'./gen/xilinx',
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT
        )
        process_handler(map_proc, verbose, map_proc_out)
        par_proc_out = open("./gen/xilinx/logs/par.log", "w+")

        print("Executing PAR...")
        par_proc = subprocess.Popen(
            ['par', '-w', '-p', '-intstyle ise', './project.ncd', './project_par.ncd', './project.pcf'],
            cwd=r'./gen/xilinx',
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT
        )
        process_handler(par_proc, verbose, par_proc_out)
        bit_proc_out = subprocess.PIPE
        if not verbose:
            bit_proc_out = open("./gen/xilinx/logs/bit.log", "w+")

        print("Generating bitfile...")
        if not os.path.exists("./gen/xilinx/bitfile"):
            os.makedirs("./gen/xilinx/bitfile")

        bit_proc = subprocess.Popen(
            ['bitgen', '-w', '-g CRC:Enable', '-intstyle ise', './project_par.ncd', './bitfile/project.bit', './project.pcf'],
            cwd=r'./gen/xilinx',
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT
        )
        process_handler(bit_proc, verbose, bit_proc_out)

        if not verbose:
            bit_proc_out.close()

    if program:
        xst_program(verbose)

def xst_program(verbose : bool):

    print("Writing cmd file for iMPACT...")
    cmd_file = open("./gen/xilinx/project.cmd", "w+")
    cmd_file.write("setMode -bscan\n")
    cmd_file.write("setCable -p auto\n")
    cmd_file.write("addDevice -p 1 -file ./bitfile/project.bit\n")
    cmd_file.write("program -p 1\n")
    cmd_file.write("quit\n")
    cmd_file.close()

    print("Executing iMPACT...")
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

def xst_simulate(files, simmod, bcon : BuildConfig):
    if not os.path.exists("./gen/xilinx/simulation"):
        os.makedirs("./gen/xilinx/simulation")

    sim_file = open("./gen/xilinx/simulation/sim.prj", "w+")

    for i in files:
        file_ext = os.path.splitext(i)
        if len(file_ext) < 2:
            continue

        if file_ext[1] == ".vhd":
            sim_file.write("vhdl work ../../" + str(i).replace('\\', '/') + "\n")
        elif file_ext[1] == ".v":
            sim_file.write("verilog work ../../" + str(i).replace('\\', '/') + "\n")

    print("Writing tcl batch file...")
    file_tcl = open("./gen/xilinx/simulation/bat.tcl", "w+")
    file_tcl.write("onerror {resume}\nwave add /")
    file_tcl.close()

    be_quiet = open(os.devnull, "w")

    print("Executing fuse...")
    fuse_proc = subprocess.Popen(
        ["fuse", "-prj", "./sim.prj", "-top", simmod, "-o", "./xst_sim.exe"],
        cwd="./gen/xilinx/simulation",
        stdout=be_quiet
    )

    process_handler(fuse_proc, False, None)

    print("Executing iSim...")
    subprocess.Popen(
        ["xst_sim", "-gui", "-tclbatch", "./bat.tcl"],
        cwd="./gen/xilinx/simulation",
        stdout=be_quiet
    )

    be_quiet.close()