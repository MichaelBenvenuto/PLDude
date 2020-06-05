import os
import subprocess

from BuildConfig import BuildConfig


#TODO:
# Write XST generation script
# Isolate toolchain directories (XST, Quartus, etc.)

class XstBuild(BuildConfig):
    def GetOptMode(self):
        opt = self.config_stream['optimize'].lower()
        if opt is not any(["speed", "area"]):
            return opt.upper()
        else:
            print("Unknown optimization config: " + str(opt))
            exit(2)

    def GetOptLevel(self):
        olvl = self.config_stream['opt-level']
        if olvl == 0:
            return 1
        elif olvl == 1:
            return 2

    def GetPins(self):
        return self.pin_stream['xst']

def process_handler(proc : subprocess):
    while True:
        return_code = proc.poll()
        output = proc.stdout.readline().decode("utf-8")
        if output is not '':
            print(output, end='')
        if return_code is not None:
            break
    pass

def xst(files, bcon : BuildConfig):
    if not os.path.exists("./gen/xilinx"):
        os.makedirs("./gen/xilinx")
    prj_file = open("./gen/xilinx/project.prj", "w+")
    xst_file = open("./gen/xilinx/xst.scr", "w+")

    print("Writing XST script...")
    xst_file.write("run\n-ifn ./gen/xilinx/project.prj\n")
    xst_file.write("-p " + bcon.GetDevice() + "\n")
    xst_file.write("-top " + bcon.GetTopMod() + "\n")
    xst_file.write("-ifmt " + bcon.GetFileType() + "\n")
    xst_file.write("-opt_mode " + bcon.GetOptMode() + "\n")
    xst_file.write("-opt_level " + str(bcon.GetOptLevel()) + "\n")
    xst_file.write("-ofn ./gen/xilinx/project.ngc\n")
    xst_file.write("-ofmt ngc")

    print("Writing project files to main file...")

    for i in files:
        prj_str = "work " + i + '\n'
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
        ['xst', '-ifn ./gen/xilinx/xst.scr', '-ofn ./gen/xilinx/project_result.srp', '-intstyle xflow'],
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
        ['ngdbuild', '-p', bcon.GetDevice(), '-dd ./gen/xilinx', '-uc ./gen/xilinx/project.ucf', './gen/xilinx/project.ngc', './gen/xilinx/project.ngd'],
        stdout=subprocess.PIPE)

    process_handler(ngd_proc)
    print("Executing MAP...")
    map_proc = subprocess.Popen(
        ['map', '-detail', '-pr b', '-p', bcon.GetDevice(), './gen/xilinx/project.ngd'],
        stdout=subprocess.PIPE
    )

    process_handler(map_proc)
