import os
import sys
import logging
import yaml
import glob
import shutil
import subprocess
import difflib

from typing import Any, IO, List

from pldude.resources import ResourceManager
from pldude.utils import PLDudeError, ConsoleFormatter, FileFormatter, RepFile

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
        from . import Xilinx7
        from . import Altera

        if shutil.which('quartus_sh') != None:
            self.__class__ = Altera
            if self.CheckPart(self.device.upper()):
                return self

        if shutil.which('vivado.bat') != None:
            self.__class__ = Xilinx7
            if self.CheckPart(self.device.lower()):
                return self

        raise PLDudeError(f'Device \'{self.device.lower()}\' was not found in any tools...', 3)

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

    def _CheckPartCmd(self) -> List[str]:
        return []

    def CheckPart(self, part : str) -> bool:
        part_listing = self._CheckPartCmd()
        possible_part = difflib.get_close_matches(part, part_listing, n=1)
        if len(possible_part) == 0:
            return False

        if possible_part[0] != part:
            raise PLDudeError(f'Part \'{part}\' could not be found (did you mean \'{possible_part[0]}\'?)', 2)

        return True

    def program(self):
        raise PLDudeError("Unknown device! Cannot program!", 3)

    def compile(self):
        raise PLDudeError("Unknown device! Cannot synthesize", 3)

    def simulate(self):
        raise PLDudeError("Unknown device! Cannot simulate", 3)