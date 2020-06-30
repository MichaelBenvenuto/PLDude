# PLDude
_A command line utility to generate bitstreams and various programming files easily for PLDs_

PLDude aims to decrease the overhead of programming PLDs (Devices like **FPGAs** and **CPLDs**) by only requiring
vendor synthesis tools and a text editor of your choosing. By abstracting away various parts of vendor-specific
tools under a common buildfile, only one instance of PLDude needs to be on your system for multiple projects.

PLDude currently only supports Xilinx and Altera tools, but, since this is written in python, many other vendors
like Lattice are planned to be supported in the future.

## Setup

### Installing the required software
PLDude only requires the command line tools of certain vendors to run; only one needs to be installed for PLDude to
be of any use. It is recommended that users install vendor specific IDEs to ensure they have proper software, again,
this is not needed.

### Building PLDude
`pyinstaller` is required to package the python script files into an executable. Ensure that it is installed by
running:

```
pip install pyinstaller
```

After pyinstaller is installed, simply run `build.py` to generate the executable:

```
python3 ./build.py
```

### Setting proper environment variables
Ensure that the PATH environment variable has the location of any command line tools added. Note that altera quartus
requires individual device family libraries to be installed before using the tool.

#### Path location for Xilinx ISE
`<ISE INSTALL LOCATION>/bin/nt` (32bit)

`<ISE INSTALL LOCATION>/bin/nt64` (64bit)

#### Path location for Xilinx Vivado
`<VIVADO INSTALL LOCATION>/bin`

#### Path location for Altera Quartus
`<ALTERA INSTALL LOCATION>/quartus/bin` (32bit)

`<ALTERA INSTALL LOCATION>/quartus/bin64` (64bit)

#### Additional Environment Variables for Xilinx ISE
For simulation using iSim-ISE, additional environment variables will be needed, these are:

`XILINX = <ISE INSTALL LOCATION>`

`PLATFORM = nt64` (Use `nt` for 32 bit)

`LD_LIBRARY_PATH = <XILINX>\lib\<PLATFORM>` (Priority, dynamic linking occurs in this directory for iSim)

If these environment variables are not defined, a segfault will occur and iSim will not run for 6-Series devices. Optionally, you can
replace the path location defined earlier with:

`<XILINX>/bin/<PLATFORM>`

## Running
PLDude has several command line arguments to choose from. These enable programming and may disable the compilation and only program the
device defined in `pldprj.yml` with a pre-generated bitfile

Option          | Functionality
----------------|--------------
default         |Only compile HDL source files
-p              |Both compile and program the device
-po             |Only program the device
-v              |Enable output to console
-sim [module]   |Simulate file (Overrides other args)

```
pldude <options>
```

It should be noted that `hw_server.bat` inside the Vivado directory requires firewall permission on port 3121. A
pop-up should be presented on the first run of `hw_server` asking for permission. In some instances, the subprocess
of `hw_server` does not close properly, kill the process manually if this happens.

Using `-sim` without the corresponding file argument will prompt the user for a file to input before simulation

## Configuration files

PLDude uses YAML files to provide a clean abstract configuration interface and supports both common settings and
vendor specific settings. **It is strongly recommended that users keep all filenames and modules the same!**

As of right now, there are only several different settings within `pldprj.yml`, these settings do the following:

Setting   | Functionality
----------|:--------------
device    |Determines the type of device the synthesizer is going to target, PLDude automatically picks a vendor based on the device chosen (eg. *XC6SLX9-2FTG256*)
filetype* |Determines the language of each file (*VHDL*/*Verilog*/*Mixed*)
optimize* |Determines how the synthesizer should optimize the top-level module (*Speed*/*Area*)
opt-level*|The level of optimization that should be performed (*0*/*1*)
top       |The top module, this is **NOT** the file it is in
src*      |The directory where source files are located
devsrc*   |The directory within src where device specific source files are located, these are package independent so for an FPGA such as the *XC6SLX9-2FTG256*, only *XC6SLX9* is required for the respective folder, folders with the names of each device will be in the directory specified by devsrc

**optional*

## Pin files

PLDude also uses YAML files to map pins, located in the file `pldpin.yml`. The basic format of this YAML file looks
like the following:
```yml
xst:
    clk: T7
    reset: A9

xilinx7:
    clk: T8
    reset: R4

altera:
    clk: R8
    reset: A2
```

Multiple pin configurations can be defined in a singular file, the format is as follows:
```yml
<BRAND>:
    <I/O NAME>: <PHYSICAL PIN>
```

Key         |Meaning
------------|---------
Brand       |The synthesizer tool to use (xst, altera, etc.)
I/O name    |The name of the respective port in the top level file
Physical Pin|The pin mapping on the actual device

## Bitfile generation
Bitfiles are automatically placed inside `./gen/[brand]/bitfile`. For xilinx this file is named `project.bit` and
for altera it is named `project.sof`