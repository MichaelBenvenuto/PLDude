from genericpath import getmtime
import logging
import sys
import os
import io
import shutil
from typing import Any, IO, Match
from pldude.utils.error import PLDudeError
import yaml
import re
import glob
import subprocess

class CustomFormatter(logging.Formatter):
    
    FORMATS = {
        logging.DEBUG : '\u001b[32m',
        logging.INFO : '\u001b[32;1m',
        logging.WARNING : '\u001b[33;1m',
        logging.ERROR : '\u001b[31;1m',
        logging.CRITICAL : '\u001b[31m'
    }
    
    def format(self, record : logging.LogRecord):
        log_fmt = '[' + self.FORMATS.get(record.levelno, '\u001b[0m') + '%(levelname)s\u001b[0m] %(message)s'
        formatter = logging.Formatter(log_fmt)
        return formatter.format(record)

class BuildConfig():

    REQUIRED_PROJ_PARAMS = ('device', 'top')

    def __init__(self):
        self._compile = False
        self._program = False
        self._simulate = False
        self._to_simulate = ""
        self._ignore = []
        self._clean = False
        self._subprocesses = []

        self._logging = logging.getLogger()
        ch = logging.StreamHandler()
        ch.setLevel(logging.DEBUG)
        ch.setFormatter(CustomFormatter())
        self._logging.addHandler(ch)

        self._logging.setLevel(logging.INFO)

        try:
            project_yaml = open("pldprj.yml", "r")
            pinproj_yaml = open("pinprj.yml", "r")
        except OSError as err:
            raise PLDudeError("Could not open " + err.filename + ": " + err.strerror, 2)

        project = yaml.load(project_yaml, Loader=yaml.SafeLoader) or {}
        self.pinconf = yaml.load(pinproj_yaml, Loader=yaml.SafeLoader) or {}

        project_yaml.close()
        pinproj_yaml.close()

        self.device = project.get('device', None)
        self.top = project.get('top', None)
        self.mode = project.get('filetype', "mixed").upper()
        self.src_dir = project.get('src', './src')
        self.vhdl_2008 = project.get('vhdl2008', False)
        self._ignore = project.get('ignore', self._ignore)

        key_errors = []
        for key in self.REQUIRED_PROJ_PARAMS:
            if not key in project.keys():
                key_errors.append(key)

        if len(key_errors) != 0:
            raise PLDudeError("Missing project parameters: " + ', '.join(key_errors), 1)

    def SetCompile(self, val : bool):
        self._compile = val

    def SetProgram(self, val : bool):
        self._program = val

    def SetSimulate(self, val : bool, module : str):
        self._simulate = val
        self._to_simulate = module

    def Clean(self, val : bool):
        self._clean = val

    def SetVerbosity(self, val : str):
        level = val.upper()
        if level == 'DEBUG':
            self._logging.setLevel(logging.DEBUG)
        elif level == 'INFO':
            self._logging.setLevel(logging.INFO)
        elif level == 'WARNING':
            self._logging.setLevel(logging.WARNING)
        elif level in ('ERROR', 'NONE'):
            self._logging.setLevel(logging.ERROR)
        elif level == 'CRITICAL':
            self._logging.setLevel(logging.CRITICAL)
        else:
            self._logging.setLevel(logging.CRITICAL)
            raise PLDudeError("Verbosity expected to be: (DEBUG | INFO | WARNING | ERROR | CRITICAL)", 2)

    def GetSpecific(self) -> 'BuildConfig':
        if self.device[0:3] == 'XC7':
            self.__class__ = Xilinx7
            return self
        return self

    def GetDirectory(self, module : str) -> str:
        directory =  "./gen/" + self.__class__.__name__ + "/" + module
        if not os.path.exists(directory):
            os.makedirs(directory)
        return directory

    def PrintLogs(self, logfile : IO[bytes]):
        pass

    def Terminate(self):
        for i in self._subprocesses:
            if not i.poll():
                i.terminate()

    def RunSubprocess(self, msg : str, cwd : str, args : list):
        self._logging.info(msg)
        subproc = subprocess.Popen(
            args,
            cwd=cwd,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT
        )
        self._subprocesses.append(subproc)
        self.PrintLogs(subproc.stdout)

    def run(self):
        if self.mode == "MIXED":
            glob_dir = self.src_dir + "/**/*[.vhd,.vhdl,.v]"
        elif self.mode == "VHDL":
            glob_dir = self.src_dir + "/**/*[.vhd,.vhdl]"
        elif self.mode == "VERILOG":
            glob_dir = self.src_dir + "/**/*.v"
        self._files = glob.glob(glob_dir, recursive=True)

        update = False
        timestamps_yml = {}
        if os.path.exists("./gen/timestamp.yml"):
            timestamps = open("./gen/timestamp.yml", "r")
            timestamps_yml = dict(yaml.load(timestamps, Loader=yaml.FullLoader))
            update = update or (timestamps_yml.get('./pinprj.yml', None) != int(os.path.getmtime('./pinprj.yml')))
            update = update or (timestamps_yml.get('./pldprj.yml', None) != int(os.path.getmtime('./pldprj.yml')))
            for i in self._files:
                if int(os.path.getmtime(i)) != timestamps_yml.get(i, None):
                    update = True
                    timestamps.close()
                    break
            timestamps.close()
        else:
            update = True

        if self._simulate:
            self.simulate()
        else:
            if self._compile and update:
                self.compile()
            elif self._compile:
                self._logging.warning("Skipping synthesis: no changes detected")

            if self._program:
                self.program()

        if self._clean and self._compile and not self._program:
            self._logging.warning("Skipping clean: compile flag set without program flag")
        elif self._clean and not self._compile:
            if not os.path.exists('./gen'):
                raise PLDudeError('Nothing to clean', 0, logging.INFO)
            self._logging.info('Cleaning...')
            try:
                shutil.rmtree('./gen', ignore_errors=True)
                sys.exit(0)
            except OSError as err:
                raise PLDudeError(err.strerror, 2)

        timestamps_yml.update({
            './pinprj.yml' : int(os.path.getmtime('./pinprj.yml')),
            './pldprj.yml' : int(os.path.getmtime('./pldprj.yml'))
        })

        for i in self._files:
            timestamps_yml.update({
                i: int(os.path.getmtime(i))
            })

        timestamps = open("./gen/timestamp.yml", "w+")
        yaml.dump(timestamps_yml, timestamps)
        timestamps.close()

    def program(self):
        raise PLDudeError("Unknown device! Cannot program!", 3)

    def compile(self):
        raise PLDudeError("Unknown device! Cannot synthesize", 3)

    def simulate(self):
        raise PLDudeError("Unknown device! Cannot simulate", 3)

class Xilinx7(BuildConfig):

    def PrintLogs(self, logfile : IO[bytes]):
        exit = False
        for i in logfile:
            vivado_match = re.match("(INFO|WARNING|ERROR|CRITICAL): \[(.*)] (.*)", i.decode())
            if vivado_match:
                match = False
                for x in self._ignore:
                    if re.match(x, vivado_match.group(2)):
                        match = True
                        break
                if match and vivado_match.group(1) == 'WARNING':
                    continue
                
                vivado_param = '[\u001b[30;1m' + vivado_match.group(2) + '\u001b[0m] '
                # bring tool info level messages downto debug for PLDude
                if vivado_match.group(1) == 'INFO':
                    self._logging.debug(vivado_param + vivado_match.group(3))
                else:
                    exit = exit or vivado_match.group(1) in ('ERROR', 'CRITICAL')
                    getattr(self._logging, vivado_match.group(1).lower())(vivado_param + vivado_match.group(3))
        if exit:
            sys.exit(2)

    def compile(self):
        compile_dir = self.GetDirectory("compile")
        bitfile_dir = self.GetDirectory("compile/bitfile")

        xilinx7_synthfile = open(compile_dir + "/synth.tcl", "w+")
        self._logging.info("Writing to TCL script...")

        xilinx7_synthfile.write("create_project -in_memory -part \"" + self.device + "\"\n")
        if self.vhdl_2008:
            xilinx7_synthfile.write("set_property enable_vhdl_2008 1 [current_project]\n")

        for i in self._files:
            file_ext = os.path.splitext(i)
            if len(file_ext) < 2:
                continue

            if file_ext[1] in (".vhd", ".vhdl"):
                file_args = ""
                if self.vhdl_2008:
                    file_args = '-vhdl2008 '
                xilinx7_synthfile.write("read_vhdl " + file_args + "../../../" + str(i).replace('\\', '/') + "\n")
            elif file_ext[1] in (".v"):
                xilinx7_synthfile.write("read_verilog ../../../" + str(i).replace('\\', '/') + "\n")

        self._logging.info("Configuring synthesis...")

        xilinx7_synthfile.write("synth_design -flatten_hierarchy none -top " + self.top + " -part " + self.device + "\n")
        xilinx7_synthfile.write("opt_design -retarget -propconst -bram_power_opt -verbose\n")
        xilinx7_synthfile.write("write_checkpoint -incremental_synth -force ./post_synth.dcp\n")

        xilinx7_synthfile.close()

        self._logging.info("Configuring place and route...")
        xilinx7_parfile = open(compile_dir + "/par.tcl", "w+")
        xilinx7_parfile.write("open_checkpoint ./post_synth.dcp\n")
        xilinx7_parfile.write("read_xdc ./pins.xdc\n")
        xilinx7_parfile.write("place_design\n")
        xilinx7_parfile.write("route_design -directive Explore\n")
        xilinx7_parfile.write("write_checkpoint -force ./post_par.dcp\n")

        xilinx7_parfile.close()

        self._logging.info("Configuring bitstream write...")
        xilinx7_bitfile = open(compile_dir + "/bit.tcl", "w+")
        xilinx7_bitfile.write("open_checkpoint ./post_par.dcp\n")
        xilinx7_bitfile.write("write_bitstream -force ./bitfile/project.bit\n")
        xilinx7_bitfile.close()

        self._logging.info("Generating XDC file...")
        xilinx7_xstfile = open(compile_dir + "/pins.xdc", "w+")
        xilinx7_xstfile.write('set_property CFGBVS VCCO [current_design];\n')
        xilinx7_xstfile.write('set_property CONFIG_VOLTAGE 3.3 [current_design];\n')
        for i in self.pinconf.get('Xilinx7').items():
            if type(i[1]) == str:
                xilinx7_xstfile.write("set_property -dict { PACKAGE_PIN " + str(i[1]) + " IOSTANDARD LVCMOS33 } [get_ports { " + str(i[0]) + " }];\n")
            elif type(i[1]) == dict:
                xilinx7_xstfile.write("set_property -dict { PACKAGE_PIN " + str(i[1]['pkg']) + " IOSTANDARD " + str(i[1]['iostd']) + " } [get_ports { " + str(i[0]) + " }];\n")
        xilinx7_xstfile.close()

        self.RunSubprocess("Executing synthesis...", compile_dir, ['vivado.bat', '-mode', 'batch', '-source', './synth.tcl'])
        self.RunSubprocess("Executing place and route...", compile_dir, ['vivado.bat', '-mode', 'batch', '-source', './par.tcl'])
        self.RunSubprocess("Executing bitstream generation...", compile_dir, ['vivado.bat', '-mode', 'batch', '-source', './bit.tcl'])

    def program(self):
        pass
        
    def simulate(self):
        sim_dir = self.GetDirectory("simulation")
        sim_file = open(sim_dir + "/sim.prj", "w+")
        self._logging.info("Writing simulation project file...")

        for i in self._files:
            file_ext = os.path.splitext(i)
            if len(file_ext) < 2:
                continue

            file_line = "work ../../../" + str(i).replace('\\', '/') + "\n"
            if file_ext[1] in (".vhd", ".vhdl"):
                if self.vhdl_2008:
                    file_line = "vhdl2008 " + file_line
                else:
                    file_line = "vhdl " + file_line
            elif file_ext[1] == ".v":
                file_line = "verilog " + file_line

            sim_file.write(file_line)

        sim_file.close()

        if not os.path.exists(sim_dir + "/bat.tcl"):
            self._logging.info("Writing tcl batch file...")
            file_tcl = open(sim_dir + "/bat.tcl", "w+")
            file_tcl.write("create_wave_config; add_wave /; set_property needs_save false [current_wave_config]")
            file_tcl.close()

        self.RunSubprocess('Executing xelab...', sim_dir, ["xelab.bat", "-prj", "./sim.prj", "-debug", "typical", "-s", "sim.out", "work." + self._to_simulate])

        self._logging.info('Executing iSim...')
        isim_prog = subprocess.Popen(
            ['xsim.bat', 'sim.out', '-gui', '-tclbatch', './bat.tcl'],
            cwd = sim_dir,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            stdin=subprocess.DEVNULL,
            creationflags= subprocess.DETACHED_PROCESS | subprocess.CREATE_NEW_PROCESS_GROUP
        )