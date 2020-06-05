# PLDude
_A command line utility to generate bitstreams and various programming files easily for PLDs_

PLDude aims to decrease the overhead of programming PLDs (Devices like **FPGAs** and **CPLDs**) by only requiring vendor synthesis tools and a text editor of your choosing. By abstracting away various parts of vendor-specific tools under a common buildfile, only one instance of PLDude needs to be on your system for multiple projects.

PLDude currently only supports Xilinx tools, but, since this is written in python, many other vendors like Lattice and Altera are going to be supported in the future.

## Configuration files

PLDude uses YAML files to provide a clean abstract configuration interface and supports both common settings and vendor specific settings. 

As of right now, there are only several different settings within `pldprj.yml`, these settings do the following:

Setting | Functionality
--------|:--------------
Device  |Determines the type of device the synthesizer is going to target, PLDude automatically picks a vendor based on the device chosen (eg. *XC6SLX9-2FTG256*)
Filetype |Determines the language of each file (*VHDL*/*Verilog*/*Mixed*)
Optimize |Determines how the synthesizer should optimize the top-level module (*Speed*/*Area*)
Opt-level|The level of optimization that should be performed (*0*/*1*)
Top      |The top module (**THE ENTITY/COMPONENT - NOT THE FILE**)
