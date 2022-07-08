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

from typing import Any, IO, Match, List
from pldude.utils.error import PLDudeError
from typing import Union
from genericpath import getmtime
from pldude.resources import ResourceManager

class ConsoleFormatter(logging.Formatter):
    
    FORMATS = {
        logging.DEBUG : '\u001b[32m',
        logging.INFO : '\u001b[32m',
        logging.WARNING : '\u001b[33m',
        logging.ERROR : '\u001b[31m',
        logging.CRITICAL : '\u001b[31m'
    }
    
    def format(self, record : logging.LogRecord):
        log_fmt = '[' + self.FORMATS.get(record.levelno, '\u001b[0m') + '%(levelname)s\u001b[0m]'
        if record.__dict__.get('synth_param', None) != None:
            log_fmt += '[\u001b[94m%(synth_param)s\u001b[0m]'
        log_fmt += ' %(message)s'
        formatter = logging.Formatter(log_fmt)
        return formatter.format(record)

class FileFormatter(logging.Formatter):
    def format(self, record : logging.LogRecord):
        log_fmt = '%(asctime)s - %(levelname)s - '
        if record.__dict__.get('synth_param', None) != None:
            log_fmt += '(%(synth_param)s) - '
        log_fmt += '%(message)s'
        formatter = logging.Formatter(log_fmt)
        return formatter.format(record)

class RepFile():
    def __init__(self, dir : str, type : str):
        self.dir = dir
        self.type = type

class BuildConfig(ResourceManager):

    REQUIRED_PROJ_PARAMS = ('device', 'top')

    _files : List[RepFile]

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
        ch.setFormatter(ConsoleFormatter())

        if not os.path.exists('./logs'):
            os.mkdir('./logs')

        fh = logging.FileHandler('./logs/pldude.log', 'w+')
        fh.setLevel(logging.DEBUG)
        fh.setFormatter(FileFormatter())

        self._logging.addHandler(ch)
        self._logging.addHandler(fh)

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

    def GetTCLPins(self, default_io_std : str) -> List[str]:
        pins = self.pinconf.get(self.__class__.__name__, {})
        pins_out = []

        pin_errs = []

        for name, val in pins.items():
            pin_str = '\"IO;'
            if type(val) == dict:
                pin_pkg = val.get('pkg', None)
                pin_std = val.get('iostd', None)

                if pin_pkg == None or pin_std == None:
                    pin_errs.append(name)
                    continue

                pin_str += f'{name};{pin_pkg};{pin_std}'
            elif type(val) == str:
                pin_str += f'{name};{val};{default_io_std}'
            pin_str += '\"'
            pins_out.append(pin_str)

        if len(pin_errs) > 0:
            pin_errs_str = ', '.join(pin_errs)
            raise PLDudeError(f'Must specify both \'pkg\' and \'iostd\' in pinprj.yml for {pin_errs_str}', 4)

        return pins_out

    def GetTCLFiles(self) -> List[str]:
        files = []
        for i in self._files:
            newdir = i.dir.replace('\\', '/')
            files.append(f"\"FILE;{i.type.upper()};{newdir}\"")
        return files

    def PrintLogs(self, logfile : IO[bytes], logger : logging.Logger = None):
        pass

    def Terminate(self):
        for i in self._subprocesses:
            if not i.poll():
                i.terminate()

    def RunSubprocess(self, msg : str, cwd : str, args : List[str], block : bool = True, user_input : bool = False, run : str = None):
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

            logger = logging.Logger(args[0], logging.INFO)
            if not os.path.exists(f'./logs/{self.__class__.__name__}'):
                os.mkdir(f'./logs/{self.__class__.__name__}')

            if run != None:
                dir = f'./logs/{self.__class__.__name__}/{run}-{args[0]}.log'
            else:
                dir = f'./logs/{self.__class__.__name__}/{args[0]}.log'
            fh = logging.FileHandler(dir, 'w+')
            fh.setFormatter(FileFormatter())
            logger.addHandler(fh)

            self.PrintLogs(subproc.stdout, logger)
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

    def PrintLogs(self, logfile : Union[IO[bytes], list], logger : logging.Logger = None):
        exit = False
        for i in logfile:
            vivado_match = re.match("(PLDUDE|INFO|WARNING|ERROR|CRITICAL): (?:\[(.*)] )?(.*)", i.decode())
            if vivado_match:
                match = False
                for x in self._ignore:
                    if re.match(x, vivado_match.group(2)):
                        match = True
                        break
                if match and vivado_match.group(1) == 'WARNING':
                    continue
                
                vivado_param = vivado_match.group(2)
                # bring tool info level messages downto debug for PLDude
                if vivado_match.group(1) == 'INFO':
                    getattr(logger, vivado_match.group(1).lower())(vivado_match.group(3).strip(), extra={'synth_param' : vivado_param})
                    self._logging.debug(vivado_match.group(3).strip(), extra={'synth_param' : vivado_param})
                elif vivado_match.group(1) == 'PLDUDE':
                    self._logging.info(vivado_match.group(3).strip())
                else:
                    exit = exit or vivado_match.group(1) in ('ERROR', 'CRITICAL')

                    # Used to get respective logging function from logger
                    getattr(logger, vivado_match.group(1).lower())(vivado_match.group(3).strip(), extra={'synth_param' : vivado_param})
                    getattr(self._logging, vivado_match.group(1).lower())(vivado_match.group(3).strip(), extra={'synth_param' : vivado_param})
        if exit:
            sys.exit(2)

    def compile(self):
        compile_dir = self.GetDirectory("compile")

        comp_args = ['vivado.bat', '-mode', 'batch', '-source', self.GetResourceDir('comp.tcl'), '-tclargs', self.device, self.top, str(self.vhdl_2008)]
        comp_args.extend(self.GetTCLFiles())
        comp_args.extend(self.GetTCLPins('LVCMOS33'))

        if not os.path.exists(self.GetDirectory('compile/bitfile')):
            os.mkdir(self.GetDirectory('compile/bitfile'))
        
        self.RunSubprocess("Executing Vivado run...", compile_dir, comp_args, run='comp')

        self._endargs.update({
            'compile': True
        })

    def program(self):
        program_dir = self.GetDirectory('program')
        hw_server_prog = self.RunSubprocess('Starting JTAG hardware server...', program_dir, ['hw_server.bat'], False)

        device = self.ListDevices()

        if not os.path.exists(self.GetDirectory('compile/bitfile') + '/project.bit'):
            self.compile()

        hw_client_prog = self.RunSubprocess('Programming device...', program_dir, ['vivado.bat', '-mode', 'tcl'], False, True, run='prog')

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
            stdin=subprocess.DEVNULL
        )
        isim_prog.wait()
        self._endargs.update({
            'simulate': True
        })

class AlteraDevice(Device):...

class Altera(BuildConfig):
    def PrintLogs(self, logfile : Union[IO[bytes], list], logger : logging.Logger = None):
        regex = re.compile('^(Info|(?:Critical )?Warning|Error|Critical)[:]? (?:\\((.*)\\): )?(.*)')
        exit = False
        for i in logfile:
            m = regex.match(i.decode())
            if m:
                altera_param = None
                altera_func = m.group(1).lower()
                file_func = altera_func
                if m.group(2):
                    altera_param = m.group(2)

                if m.group(1) == 'Info':
                    if m.group(3)[0:5] != '*****':
                        altera_func = 'debug'
                    else:
                        logger.info(m.group(3).strip())
                        continue
                elif m.group(1) == 'Critical Warning':
                    altera_func = 'warning'
                    file_func = altera_func
                exit = exit or m.group(1).upper() in ('ERROR', 'CRITICAL')
                getattr(logger, file_func)(m.group(3).strip(), extra={'synth_param' : altera_param})
                getattr(self._logging, altera_func)(m.group(3), extra={'synth_param' : altera_param})
        
        if exit:
            sys.exit(2)

    def compile(self):
        compile_dir = self.GetDirectory('compile')
        bitfile_dir = self.GetDirectory('compile/bitfile')

        pins = ['quartus_sh', '-t', os.path.abspath(self.GetResourceDir('qsf.tcl')), self.device, self.top]
        altera_pconf = self.pinconf.get(self.__class__.__name__, None)
        if altera_pconf == None:
            raise PLDudeError('Pin configuration does not exist for ' + self.__class__.__name__, 2)

        pins.extend(self.GetTCLFiles())
        pins.extend(self.GetTCLPins('LVCMOS'))

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