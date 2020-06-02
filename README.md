# PLDude
_A command line utility to generate bitstreams and various programming files easily for PLDs_

PLDude aims to decrease the overhead of programming PLDs (Devices like **FPGAs** and **CPLDs**) by only requiring vendor synthesis tools and a text editor of your choosing. By abstracting away various parts of vendor-specific tools under a common buildfile, only one instance of PLDude needs to be on your system for multiple projects.

PLDude currently only supports Xilinx tools, but, since this is written in python, many other vendors like Lattice and Altera are going to be supported in the future.

## Configuration files

PLDude uses YAML files to provide a clean abstract configuration interface and supports both common settings and vendor specific settings. 