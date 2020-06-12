import os
import subprocess
import signal

from BuildConfig import BuildConfig
from BuildConfig import process_handler
from build_xst import XstBuild

from sys import exit

class Xst7Build(XstBuild):
    def GetPins(self):
        if not 'xilinx7' in self.pin_stream:
            print("No pin configuration found for Xilinx 7!")
            exit(-5)
        return self.pin_stream['xilinx7']

    def Run(self, files, program, only_program, verbose):
        xst7(files, self, program, only_program, verbose)

def xst7(files, bcon : BuildConfig, program : bool, only_program : bool, verbose : bool):
    if not os.path.exists("./gen/xilinx7/"):
        os.makedirs("./gen/xilinx7/")

    if not os.path.exists("./gen/xilinx7/bitfile"):
        os.makedirs("./gen/xilinx7/bitfile")

    if not (program and only_program):
        xst7_synthfile = open("./gen/xilinx7/synth.tcl", "w+")
        print("Writing to TCL script...")
        xst7_synthfile.write("create_project -in_memory -part \"" + bcon.GetDevice() + "\"\n")
        for i in files:
            file_ext = os.path.splitext(i)
            if len(file_ext) < 2:
                continue

            if file_ext[1] == ".vhd":
                xst7_synthfile.write("read_vhdl ../../" + str(i).replace('\\', '/') + "\n")
            elif file_ext[1] == ".v":
                xst7_synthfile.write("read_verilog " + str(i).replace('\\', '/') + "\n")

        print("Configuring synthesis...")
        xst7_synthfile.write("read_xdc ./pins.xdc\n")
        xst7_synthfile.write("synth_design -top " + bcon.GetTopMod() + " -part " + bcon.GetDevice() + "\n")
        xst7_synthfile.write("opt_design\n")
        xst7_synthfile.write("write_checkpoint -incremental_synth -force ./post_synth.dcp\n")
        xst7_synthfile.close()

        print("Configuring place and route...")
        xst7_parfile = open("./gen/xilinx7/par.tcl", "w+")
        xst7_parfile.write("open_checkpoint ./post_synth.dcp\n")
        xst7_parfile.write("place_design\n")
        xst7_parfile.write("route_design -directive Explore\n")
        xst7_parfile.write("write_checkpoint -force ./post_par.dcp")
        xst7_parfile.close()

        print("Configuring bitstream write...")
        xst7_bitfile = open("./gen/xilinx7/bit.tcl", "w+")
        xst7_bitfile.write("open_checkpoint ./post_par.dcp\n")
        xst7_bitfile.write("write_bitstream -force ./bitfile/project.bit\n")
        xst7_bitfile.close()


        print("Generating XDC file...")
        xst7_xdcfile = open("./gen/xilinx7/pins.xdc", "w+")
        pins = bcon.GetPins()
        for i in pins:
            xst7_xdcfile.write("set_property -dict { PACKAGE_PIN " + str(pins[i]) + " IOSTANDARD LVCMOS33 } [get_ports { " + str(i) + " }];\n")
        xst7_xdcfile.close()

        print("Executing synthesis...")
        synth_prog_out = subprocess.PIPE
        if not verbose:
            if not os.path.exists("./gen/xilinx7/logs"):
                os.makedirs("./gen/xilinx7/logs")
            synth_prog_out = open("./gen/xilinx7/logs/synth.log", "w+")

        synth_prog = subprocess.Popen(
            ["vivado.bat", "-mode", "batch", "-source", "./synth.tcl"],
            cwd="./gen/xilinx7",
            stdout=synth_prog_out
        )
        process_handler(synth_prog)

        print("Executing place and route...")
        par_prog_out = subprocess.PIPE
        if not verbose:
            par_prog_out = open("./gen/xilinx/logs/par.log")
            synth_prog_out.close()

        par_prog = subprocess.Popen(
            ["vivado.bat", "-mode", "batch", "-source", "./par.tcl"],
            cwd="./gen/xilinx7",
            stdout=par_prog_out
        )
        process_handler(par_prog)

        print("Executing bitstream generation...")
        bit_prog_out = subprocess.PIPE
        if not verbose:
            bit_prog_out = open("./gen/xilinx/logs/par.log")
            par_prog_out.close()

        bit_prog = subprocess.Popen(
            ["vivado.bat", "-mode", "batch", "-source", "./bit.tcl"],
            cwd="./gen/xilinx7",
            stdout=bit_prog_out
        )
        process_handler(bit_prog)

    if program:
        xilinx7_program(verbose)

def xilinx7_program(verbose : bool):
    print("Starting JTAG hardware server...")
    hwserv_prog_out = subprocess.PIPE
    if not verbose:
        hwserv_prog_out = open("./gen/xilinx7/logs/hw_server.log", "w+")
    hw_server_prog = subprocess.Popen(
        ['hw_server.bat'],
        cwd="./gen/xilinx7",
        stdout=hwserv_prog_out
    )

    print("Configuring JTAG programming...")
    progtcl_file = open("./gen/xilinx7/prog.tcl", "w+")
    progtcl_file.write("open_hw\n")
    progtcl_file.write("connect_hw_server -url localhost:3121\n")
    progtcl_file.write("current_hw_target [get_hw_targets */xilinx_tcf/Digilent/*]\n")
    progtcl_file.write("open_hw_target\n")
    progtcl_file.write("current_hw_device [lindex [get_hw_devices] 0]\n")
    progtcl_file.write("set_property PROGRAM.FILE {./bitfile/project.bit} [lindex [get_hw_devices] 0]\n")
    progtcl_file.write("program_hw_devices [lindex [get_hw_devices] 0]\n")
    progtcl_file.close()

    program_prog_out = subprocess.PIPE
    if not verbose:
        program_prog_out = open("./gen/xilinx7/logs/program.log", "w+")

    print("Programming device...")
    program_prog = subprocess.Popen(
        ['vivado.bat', '-mode', 'batch', '-source', './prog.tcl'],
        cwd='./gen/xilinx7',
        stdout=program_prog_out
    )

    process_handler(program_prog)
    os.kill(hw_server_prog.pid, signal.CTRL_BREAK_EVENT)