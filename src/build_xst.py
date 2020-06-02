import os

from BuildConfig import BuildConfig


#TODO:
# Write XST generation script
# Isolate toolchain directories (XST, Quartus, etc.)

class XstBuild(BuildConfig):
    def GetOptMode(self):
        opt = self.config_stream['optimize']
        if opt is "Speed":
            return "SPEED"
        elif opt is "Area":
            return "AREA"
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
    xst_file.write("run\n-ifn /gen/xilinx/project.prj\n")
    xst_file.write("-p " + bcon.GetDevice())
    xst_file.write("-top " + bcon.GetTopMod() + "\n")
    xst_file.write("-ifmt " + bcon.GetFileType() + "\n")
    xst_file.write("-opt_mode " + bcon.GetOptMode(BuildConfig.XST) + "\n")
    xst_file.write("-ofn /gen/xilinx/project.ngc")

    print("Writing project files to main file...")
    for i in files:
        prj_str = "" + bcon.file_type.lower() + " work " + i + '\n'
        prj_file.write(prj_str)
    prj_file.close()
    xst_file.close()