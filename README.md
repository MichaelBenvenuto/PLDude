# PLDude
_A command line utility to generate bitstreams and various programming files easily for PLDs_

PLDude aims to decrease the overhead of programming PLDs (Devices like **FPGAs** and **CPLDs**) by only requiring vendor synthesis tools and a text editor of your choosing. By abstracting away various parts of vendor-specific tools under a common buildfile, only one instance of PLDude needs to be on your system for multiple projects.

PLDude currently only supports Xilinx tools, but, since this is written in python, many other vendors like Lattice and Altera are going to be supported in the future.

## Configuration files

PLDude uses YAML files to provide a clean abstract configuration interface and supports both common settings and vendor specific settings. 

As of right now, there are only several different settings within `pldprj.yml`, these settings do the following:

Setting  | Functionality
---------|:--------------
Device   |Determines the type of device the synthesizer is going to target, PLDude automatically picks a vendor based on the device chosen (eg. *XC6SLX9-2FTG256*)
Filetype |Determines the language of each file (*VHDL*/*Verilog*/*Mixed*)
Optimize |Determines how the synthesizer should optimize the top-level module (*Speed*/*Area*)
Opt-level|The level of optimization that should be performed (*0*/*1*)
Top      |The top module (**THE ENTITY/COMPONENT - NOT THE FILE**)
src      |The directory where source files are located

## Pin files

PLDude also uses YAML files to map pins, located in the file ```pldpin.yml```. The basic format of this YAML file looks like the following:
```yml
xst:
    imm16[0]: T7
    imm16[1]: A9

altera:
    clk[0]: R8
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
Bitfiles are automatically placed inside ```./gen/[brand]/bitfile```