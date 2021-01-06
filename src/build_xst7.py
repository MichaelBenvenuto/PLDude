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

    def Run(self, files, program, only_program, simulate, sim_mod, verbose):
        if simulate:
            xilinx7_simulate(files, sim_mod, self)
        else:
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
        vhdl_2008 = bcon.GetVHDL2008()
        if vhdl_2008:
            xst7_synthfile.write("set_property enable_vhdl_2008 1 [current_project]\n")

        for i in files:
            file_ext = os.path.splitext(i)
            if len(file_ext) < 2:
                continue

            if file_ext[1] == ".vhd":
                file_args = ""
                if vhdl_2008:
                    file_args = "-vhdl2008"
                xst7_synthfile.write("read_vhdl " + file_args + " ../../" + str(i).replace('\\', '/') + "\n")
            elif file_ext[1] == ".v":
                xst7_synthfile.write("read_verilog ../../" + str(i).replace('\\', '/') + "\n")

        print("Configuring synthesis...")
        xst7_synthfile.write("synth_design -top " + bcon.GetTopMod() + " -part " + bcon.GetDevice() + "\n")
        xst7_synthfile.write("opt_design -retarget -propconst -bram_power_opt -verbose\n")
        xst7_synthfile.write("write_checkpoint -incremental_synth -force ./post_synth.dcp\n")
        if bcon.GetTimingReport('synth'):
            xst7_synthfile.write("report_timing_summary -file ./timing.rpt\n")

        if bcon.GetUtilizeReport('synth'):
            xst7_synthfile.write("report_utilization -file ./utilize.rpt")

        xst7_synthfile.close()

        print("Configuring place and route...")
        xst7_parfile = open("./gen/xilinx7/par.tcl", "w+")
        xst7_parfile.write("open_checkpoint ./post_synth.dcp\n")
        xst7_parfile.write("read_xdc ./pins.xdc\n")
        xst7_parfile.write("place_design\n")

        if bcon.GetTimingReport('place'):
            xst7_parfile.write("report_timing_summary -file ./place_timing.rpt\n")

        if bcon.GetUtilizeReport('place'):
            xst7_parfile.write("report_utilization -file ./place_utilize.rpt")

        xst7_parfile.write("route_design -directive Explore\n")
        xst7_parfile.write("write_checkpoint -force ./post_par.dcp\n")

        if bcon.GetClockUtilize():
            xst7_parfile.write("report_clock_utilization -file ./clock.rpt\n")

        if bcon.GetTimingReport('route'):
            xst7_parfile.write("report_timing_summary -file ./route_timing.rpt\n")

        if bcon.GetUtilizeReport('route'):
            xst7_parfile.write("report_utilization -file ./route_utilize.rpt")

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
            pin = pins[i]
            if type(pin) == str:
                xst7_xdcfile.write("set_property -dict { PACKAGE_PIN " + str(pin) + " IOSTANDARD LVCMOS33 } [get_ports { " + str(i) + " }];\n")
            elif type(pin) == dict:
                xst7_xdcfile.write("set_property -dict { PACKAGE_PIN " + str(pin['pkg']) + " IOSTANDARD " + str(pin['iostd']) + " } [get_ports { " + str(i) + " }];\n")
        xst7_xdcfile.close()

        print("Executing synthesis...")

        if not os.path.exists("./gen/xilinx7/logs"):
            os.makedirs("./gen/xilinx7/logs")

        synth_prog = subprocess.Popen(
            ["vivado.bat", "-mode", "batch", "-source", "./synth.tcl"],
            cwd="./gen/xilinx7",
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT
        )

        synth_prog_out = open("./gen/xilinx7/logs/synth.log", "w+")
        process_handler(synth_prog, verbose, synth_prog_out)
        synth_prog_out.close()

        print("Executing place and route...")

        par_prog = subprocess.Popen(
            ["vivado.bat", "-mode", "batch", "-source", "./par.tcl"],
            cwd="./gen/xilinx7",
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT
        )

        par_prog_out = open("./gen/xilinx7/logs/par.log", "w+")
        process_handler(par_prog, verbose, par_prog_out)
        par_prog_out.close()

        print("Executing bitstream generation...")

        bit_prog = subprocess.Popen(
            ["vivado.bat", "-mode", "batch", "-source", "./bit.tcl"],
            cwd="./gen/xilinx7",
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT
        )

        bit_prog_out = open("./gen/xilinx7/logs/bit.log", "w+")
        process_handler(bit_prog, verbose, bit_prog_out)
        bit_prog_out.close();

    if program:
        xilinx7_program(verbose)

def xilinx7_program(verbose : bool):
    print("Starting JTAG hardware server...")
    hwserv_prog_out = open("./gen/xilinx7/logs/hw_server.log", "w+")
    hw_server_prog = subprocess.Popen(
        ['hw_server.bat'],
        cwd="./gen/xilinx7",
        stdout=hwserv_prog_out,
        stderr=subprocess.STDOUT
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

    program_prog_out = open("./gen/xilinx7/logs/program.log", "w+")
    print("Programming device...")
    program_prog = subprocess.Popen(
        ['vivado.bat', '-mode', 'batch', '-source', './prog.tcl'],
        cwd='./gen/xilinx7',
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT
    )

    process_handler(program_prog, verbose, program_prog_out)
    os.kill(hw_server_prog.pid, signal.CTRL_BREAK_EVENT)

def xilinx7_simulate(files, sim_mod, bcon : BuildConfig):
    if not os.path.exists("./gen/xilinx7/simulation"):
        os.makedirs("./gen/xilinx7/simulation")

    sim_file = open("./gen/xilinx7/simulation/sim.prj", "w+")

    print("Writing simulation project file...")

    vhdl_2008 = bcon.GetVHDL2008()

    for i in files:
        file_ext = os.path.splitext(i)
        if len(file_ext) < 2:
            continue

        if file_ext[1] == ".vhd":
            if vhdl_2008:
                vhd_file = "vhdl2008 work ../../../" + str(i).replace('\\', '/') + "\n"
            else:
                vhd_file = "vhdl work ../../../" + str(i).replace('\\', '/') + "\n"
            sim_file.write(vhd_file)
        elif file_ext[1] == ".v":
            sim_file.write("verilog work ../../../" + str(i).replace('\\', '/') + "\n")

    sim_file.close()

    print("Writing tcl batch file...")
    file_tcl = open("./gen/xilinx7/simulation/bat.tcl", "w+")
    file_tcl.write("create_wave_config; add_wave /; set_property needs_save false [current_wave_config]")
    file_tcl.close()

    print("Executing xelab...")
    xelab_args = ["xelab.bat", "-prj", "./sim.prj", "-debug", "typical", "-s", "sim.out", "work." + sim_mod]
    xelab_prog = subprocess.Popen(
        xelab_args,
        cwd='./gen/xilinx7/simulation',
        stdout=subprocess.PIPE
    )

    process_handler(xelab_prog, False, None)

    print("Executing iSim...")
    isim_prog = subprocess.call(
        ["xsim.bat", "sim.out", "-gui", "-tclbatch", "./bat.tcl"],
        cwd='./gen/xilinx7/simulation',
        close_fds=True,
        stdout=subprocess.PIPE
    )

    process_handler(isim_prog, False, None)
