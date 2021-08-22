import logging
from posixpath import abspath
import sys
import os
import io
import shutil
import yaml
import re
import glob
import subprocess

from typing import Any, IO, Match
from pldude.utils.error import PLDudeError
from typing import Union
from genericpath import getmtime
from pldude.resources import ResourceManager

class CustomFormatter(logging.Formatter):
    
    FORMATS = {
        logging.DEBUG : '\u001b[32m',
        logging.INFO : '\u001b[32m',
        logging.WARNING : '\u001b[33m',
        logging.ERROR : '\u001b[31m',
        logging.CRITICAL : '\u001b[31m'
    }
    
    def format(self, record : logging.LogRecord):
        log_fmt = '[' + self.FORMATS.get(record.levelno, '\u001b[0m') + '%(levelname)s\u001b[0m] %(message)s'
        formatter = logging.Formatter(log_fmt)
        return formatter.format(record)

class RepFile():
    def __init__(self, dir : str, type : str):
        self.dir = dir
        self.type = type

class BuildConfig(ResourceManager):

    REQUIRED_PROJ_PARAMS = ('device', 'top')

    def __init__(self):
        self._compile = False
        self._program = False
        self._simulate = False
        self._to_simulate = ""
        self._ignore = []
        self._clean = False
        self._subprocesses = []
        self._remote = None
        self._platform_dir = None

        self._endargs = {}

        self._logging = logging.getLogger()
        ch = logging.StreamHandler()
        ch.setLevel(logging.DEBUG)
        ch.setFormatter(CustomFormatter())
        self._logging.addHandler(ch)

        self._logging.setLevel(logging.INFO)

    def LoadConfig(self):
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
        self._remote = project.get('remote', 'DEFAULT')
        self._platform_dir = project.get('platform_src', self._platform_dir)

        key_errors = []
        for key in self.REQUIRED_PROJ_PARAMS:
            if not key in project.keys():
                key_errors.append(key)

        if len(key_errors) != 0:
            raise PLDudeError("Missing project parameters: " + ', '.join(key_errors), 1)
    def GetRemote(self) -> str:
        raise PLDudeError('Unknown Device! Cannot get remote programming URL!', 2)

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
        elif self.device.upper()[0] == 'E' or self.device[0] == '5' or self.device[0:2] == '10':
            self.__class__ = Altera
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

    def RunSubprocess(self, msg : str, cwd : str, args : list, block : bool = True, user_input : bool = False):
        self._logging.info(msg)
        if user_input:
            proc_stdin = subprocess.PIPE
        else:
            proc_stdin = subprocess.DEVNULL
        subproc = subprocess.Popen(
            args,
            cwd=cwd,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            stdin=proc_stdin
        )
        self._subprocesses.append(subproc)
        if block:
            self.PrintLogs(subproc.stdout)
        return subproc

    def run(self):
        if self.mode == "MIXED":
            glob_ext = "/**/*[.vhd,.vhdl,.v]"
        elif self.mode == "VHDL":
            glob_ext = "/**/*[.vhd,.vhdl]"
        elif self.mode == "VERILOG":
            glob_ext = "/**/*.v"
        else:
            raise PLDudeError("Unknown file type: " + self.mode, 2)
        glob_dir = self.src_dir + glob_ext
        files = glob.glob(glob_dir, recursive=True)

        if self._platform_dir:
            files.extend(glob.glob(self._platform_dir + "/" + self.__class__.__name__ + glob_ext))

        self._files = []
        for i in files:
            ext = os.path.splitext(i)[1]
            path = os.path.abspath(i)
            if ext in ('.vhd', '.vhdl'):
                self._files.append(RepFile(path, 'VHDL'))
            elif ext == '.v':
                self._files.append(RepFile(path, 'VERILOG'))


        update = False
        timestamps_yml = {}
        if os.path.exists("./gen/timestamp.yml"):
            timestamps = open("./gen/timestamp.yml", "r")
            timestamps_yml = dict(yaml.load(timestamps, Loader=yaml.FullLoader))
            update = update or (timestamps_yml.get(os.path.abspath('./pinprj.yml'), None) != int(os.path.getmtime(os.path.abspath('./pinprj.yml'))))
            update = update or (timestamps_yml.get(os.path.abspath('./pldprj.yml'), None) != int(os.path.getmtime(os.path.abspath('./pldprj.yml'))))
            for i in self._files:
                if int(os.path.getmtime(i.dir)) != timestamps_yml.get(i.dir, None):
                    update = True
                    timestamps.close()
                    break
            timestamps.close()
        else:
            update = True
        try:
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

        except PLDudeError as err:
            raise err
        except Exception as err:
            self._logging.critical(err)
            self.Terminate()
            pass

        timestamps_yml.update({
            os.path.abspath('./pinprj.yml') : int(os.path.getmtime('./pinprj.yml')),
            os.path.abspath('./pldprj.yml') : int(os.path.getmtime('./pldprj.yml'))
        })

        if self._endargs.get('compile', False):
            for i in self._files:
                timestamps_yml.update({
                    i.dir: int(os.path.getmtime(i.dir))
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

class Device():...

class Xilinx7Device(Device):
    def __init__(self, target : str, device : str):
        self.target = target
        self.device = device

    def __repr__(self) -> str:
        if type(self.device) == list:
            return self.target + " (" + ' '.join(self.device) + ")"
        elif type(self.device) == str:
            return self.target + " (" + self.device + ")"

class Xilinx7(BuildConfig):
    def GetRemote(self) -> str:
        if self._remote == 'DEFAULT':
            return 'localhost:3121'
        return self._remote

    def ListDevices(self) -> Xilinx7Device:
        program_dir = self.GetDirectory('program')
        self._logging.info('Getting list of JTAG Devices...')

        hw_devices_prog = subprocess.Popen(
            ['vivado.bat', '-mode', 'tcl'],
            cwd = program_dir,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            stdin=subprocess.PIPE
        )

        scan_for_devices = self.GetResource("scan_for_devices.tcl")
        hw_devices_prog.stdin.write(b'open_hw\n')
        hw_devices_prog.stdin.write(b'connect_hw_server -url ' + self.GetRemote().encode() + b'\n')
        hw_devices_prog.stdin.write(scan_for_devices.read().encode())
        scan_for_devices.close()

        output_prog = hw_devices_prog.communicate()[0].decode()

        devices = None
        for i in output_prog.split('\r\n'):
            match = re.match("PLDUDE:(.*)", i)
            if match:
                if match.group(1) == 'BEGIN':
                    devices = []
                elif match.group(1) == 'END':
                    break
            elif type(devices) == list:
                params = i.split(' ')
                devices.append(Xilinx7Device(params[0], params[1:]))

        if len(devices) > 1:
            print('Select a target:')
            for i in range(0, len(devices)):
                print('\t[' + str(i) + ']: ' + str(devices[i]))

            target = int(input('> '))
        elif len(devices) == 1:
            target = 0
            self._logging.info('Singular target found, selecting ' + str(devices[0]))
        else:
            raise PLDudeError('No targets found', 0, logging.WARNING)

        if len(devices[target].device) > 1:
            print('Select a device:')
            for i in range(0, len(devices[target].device)):
                print('\t[' + str(i) + ']: ' + str(devices[target].device[i]))

            device = int(input('> '))
        elif len(devices[target].device) == 1:
            device = 0
            self._logging.info('Singular device found, selecting ' + str(devices[target].device[0]))

        devices[target].device = devices[target].device[device]
        return devices[target]

    def PrintLogs(self, logfile : Union[IO[bytes], list]):
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
                
                vivado_param = '[\u001b[94m' + vivado_match.group(2) + '\u001b[0m] '
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
            file_ext = os.path.splitext(i.dir)
            if len(file_ext) < 2:
                continue

            if file_ext[1] in (".vhd", ".vhdl"):
                file_args = ""
                if self.vhdl_2008:
                    file_args = '-vhdl2008 '
                xilinx7_synthfile.write("read_vhdl " + file_args + "../../../" + str(i.dir).replace('\\', '/') + "\n")
            elif file_ext[1] in (".v"):
                xilinx7_synthfile.write("read_verilog ../../../" + str(i.dir).replace('\\', '/') + "\n")

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

        self._endargs.update({
            'compile': True
        })

    def program(self):
        program_dir = self.GetDirectory('program')
        hw_server_prog = self.RunSubprocess('Starting JTAG hardware server...', program_dir, ['hw_server.bat'], False)

        device = self.ListDevices()

        if not os.path.exists(self.GetDirectory('compile/bitfile') + '/project.bit'):
            self.compile()

        hw_client_prog = self.RunSubprocess('Programming device...', program_dir, ['vivado.bat', '-mode', 'tcl'], False, True)

        hw_client_prog.stdin.write(b'open_hw\n')
        hw_client_prog.stdin.write(b'connect_hw_server -url ' + self.GetRemote().encode() + b'\n')
        hw_client_prog.stdin.write(b'current_hw_target ' + device.target.encode() + b'\n')
        hw_client_prog.stdin.write(b'open_hw_target\n')
        hw_client_prog.stdin.write(b'current_hw_device [get_hw_devices -of_objects [current_hw_target]]\n')
        hw_client_prog.stdin.write(b'set_property PROGRAM.FILE {../compile/bitfile/project.bit} [current_hw_device]\n')
        hw_client_prog.stdin.write(b'program_hw_devices [current_hw_device]\n')

        self.PrintLogs(hw_client_prog.communicate()[0].split(b'\r\n'))

        hw_client_prog.terminate()
        hw_server_prog.terminate()
        self._endargs.update({
            'program': True
        })
        
    def simulate(self):
        sim_dir = self.GetDirectory("simulation")
        sim_file = open(sim_dir + "/sim.prj", "w+")
        self._logging.info("Writing simulation project file...")

        for i in self._files:
            file_ext = os.path.splitext(i.dir)
            if len(file_ext) < 2:
                continue

            file_line = "work " + str(i.dir).replace('\\', '/') + "\n"
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
        self._endargs.update({
            'simulate': True
        })

class AlteraDevice(Device):...

class Altera(BuildConfig):
    def PrintLogs(self, logfile : Union[IO[bytes], list]):
        regex = re.compile('^(Info|(?:Critical )?Warning|Error|Critical)[:]? (?:\\((.*)\\): )?(.*)')
        exit = False
        for i in logfile:
            m = regex.match(i.decode())
            if m:
                altera_param = ''
                if m.group(2):
                    altera_param = '[\u001b[94m' + m.group(2) + '\u001b[0m] '
                if m.group(1) == 'Info':
                    if m.group(3)[0:5] != '*****':
                        self._logging.debug(altera_param + m.group(3))
                    continue
                elif m.group(1) == 'Critical Warning':
                    self._logging.warning(altera_param + m.group(3))
                    continue
                exit = exit or m.group(1).upper() in ('ERROR', 'CRITICAL')
                getattr(self._logging, m.group(1).lower())(altera_param + m.group(3))
        
        if exit:
            sys.exit(2)

    def compile(self):
        compile_dir = self.GetDirectory('compile')
        bitfile_dir = self.GetDirectory('compile/bitfile')

        pins = ['quartus_sh', '-t', os.path.abspath(self.GetResourceDir('qsf.tcl')), self.device, self.top]
        altera_pconf = self.pinconf.get(self.__class__.__name__, None)
        if altera_pconf == None:
            raise PLDudeError('Pin configuration does not exist for ' + self.__class__.__name__, 2)
        for i in self.pinconf[self.__class__.__name__].items():
            data = 'IO;' + i[0] + ';'
            if type(i[1]) == dict:
                data += ';'.join(list(i[1].values()))
            elif type(i[1]) == str:
                data += i[1] + ';LVCMOS'
            else:
                raise PLDudeError('Unknown type!', 2)

        for i in self._files:
            pins.append("FILE;" + i.type.upper() + ';' + i.dir)

        self.RunSubprocess('Creating quartus project...', compile_dir, pins)
        self.RunSubprocess('Executing synthesis...', compile_dir, ['quartus_map', 'project'])
        self.RunSubprocess('Executing fitter...', compile_dir, ['quartus_fit', 'project'])
        self.RunSubprocess('Executing assembler...', compile_dir, ['quartus_asm', 'project'])

        if os.path.exists(bitfile_dir + '/project.sof'):
            os.remove(bitfile_dir + '/project.sof')
        os.rename(compile_dir + '/project.sof', bitfile_dir + '/project.sof')
        self._endargs['compile'] = True

    def program(self):
        bitfile_dir = self.GetDirectory('compile/bitfile')
        self.RunSubprocess('Executing programmer...', bitfile_dir, ['quartus_pgm', '-m', 'JTAG', '-o', 'p;./project.sof'])
        self._endargs['program'] = True