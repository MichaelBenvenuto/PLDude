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
    xst_file.write("-ofn ./gen/xilinx/project.ngc\n")
    xst_file.write("-ofmt NGC")

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

    while True:
        return_code = xst_proc.poll()
        if return_code is not None:
            break

    print("XST has finished, check file ./gen/xilinx/project_result.srp for more info.")
