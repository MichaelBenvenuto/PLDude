import os

from BuildConfig import BuildConfig


#TODO:
# Write XST generation script
# Isolate toolchain directories (XST, Quartus, etc.)

def xst(files, bcon : BuildConfig):
    if not os.path.exists("./gen/xilinx"):
        os.makedirs("./gen/xilinx")
    prj_file = open("./gen/xilinx/project.prj", "w+")
    xst_file = open("./gen/xilinx/xst.scr", "w+")

    print("Writing XST script...")
    xst_file.write("run\n-ifn /gen/xilinx/project.prj\n")
    xst_file.write("-top " + str(bcon.top) + "\n")
    xst_file.write("-ifmt " + str(bcon.file_type) + "\n")
    xst_file.write("-opt_mode " + str(bcon.opt) + "\n")
    xst_file.write("-ofn /gen/xilinx/project.ngc")

    print("Writing project files to main file...")
    for i in files:
        prj_str = "" + bcon.file_type.lower() + " work " + i + '\n'
        prj_file.write(prj_str)
    prj_file.close()
    xst_file.close()