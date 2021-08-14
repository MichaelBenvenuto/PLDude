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
*Installing the PLDude as an executable was removed in v0.9.0*

PLDude now runs within the python environment as a module, to install it, simply run the following command in the root 
project directory:

`python setup.py install --user`

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
PLDude has several command line arguments to choose from. These can enable programming, toggle synthesis/compilation or program the device with a
prepared bitfile

Option          | Functionality
----------------|--------------
-c,--compile    |Synthesize project
-p,--program    |Upload bitfile to device
-v,--verbosity  |Set output verbosity level
-s,--simulate   |Simulate file (Overrides above arguments)
-h,--help       |Display help message
-x,--clean      |Clean tool-generated files after any specified steps, ignored if -c is set without -p

```
pldude [-c|--compile] [-p|--program] [-v|--verbosity <DEBUG|INFO|WARNING|ERROR|NONE>] [-s|--simulate <module>] [-h|--help] [-x|--clean]
```

It should be noted that `hw_server.bat` inside the Vivado directory requires firewall permission on port 3121. A
pop-up should be presented on the first run of `hw_server` asking for permission. In some instances, the subprocess
of `hw_server` does not close properly, kill the process manually if this happens. Remote programming is not yet supported

~~Using `-s,--simulate` without the corresponding file argument will prompt the user for a file to input before simulation~~

## Configuration files

PLDude uses YAML files to provide a clean abstract configuration interface and supports both common settings and
vendor specific settings. **It is strongly recommended that users keep all filenames and modules the same!**

As of right now, there are only several different settings within `pldprj.yml`, these settings do the following:

Setting         | Functionality
----------------|:--------------
device          |Determines the type of device the synthesizer is going to target, PLDude automatically picks a vendor based on the device chosen (eg. *XC6SLX9-2FTG256*)
filetype*       |Determines the language of each file (*VHDL*/*Verilog*/*Mixed*)
optimize*       |Determines how the synthesizer should optimize the top-level module (*Speed*/*Area*)
opt-level*      |The level of optimization that should be performed (*0*/*1*)
clock_report*   |Report clock statistics (*True*/*False*)
timing_reports* |List of timing statistics to report (*synth*|*place*|*route*)
util_reports*   |List of utilization statistics to report (*synth*|*place*|*route*)
top             |The top module, this is **NOT** the file it is in
src*            |The directory where source files are located
devsrc*         |The directory within src where device specific source files are located, these are package independent so for an FPGA such as the *XC6SLX9-2FTG256*, only *XC6SLX9* is required for the respective folder, folders with the names of each device will be in the directory specified by devsrc

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

In place of strings for pin mappings, an additional YAML layer can be added to the mapping string to define the package and the iostandard.
The iostandard configuration is dependent on the vendor's standards and varies between Vivado, ISE and Quartus. This should really be used
for output pins, unlike the example implies with the redefinition of 'reset', however, some tools may support input pin standards. All of
these configurations produce similar results (3.3v CMOS standard on all devices). This is an advanced feature and should be handled by experienced users.
**Damage to your board or device may occur with improper settings, use with caution**
```yml
xst:
    clk: T7
    reset:
        pkg: A9
        iostd: LVCMOS33

xilinx7:
    clk: T8
    reset:
        pkg: R4
        iostd: LVCMOS33

altera:
    clk: R8
    reset:
        pkg: A2
        iostd: LVCMOS
```

Multiple pin configurations can be defined in a singular file, the format is as follows:
```yml
<BRAND>:
    <I/O NAME>: <PHYSICAL PIN>
    <I/O Name>:
        pkg: <PHYSICAL PIN>
        iostd: <IO STANDARD>
```

Key         |Meaning
------------|---------
Brand       |The synthesizer tool to use (Xilinx7, Xilinx, Altera, etc.)
I/O name    |The name of the respective port in the top level file
I/O standard|The name of the IO standard for the given pin
Physical Pin|The pin mapping on the actual device

## Bitfile generation
Bitfiles are automatically placed inside `./gen/[brand]/bitfile`. For xilinx this file is named `project.bit` and
for altera it is named `project.sof`