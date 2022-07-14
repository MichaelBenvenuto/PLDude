import sys
import os
import shutil
import subprocess
import logging
import re

from pldude.bconfigs import BuildConfig
from pldude.utils import Device, PLDudeError

from typing import Union, IO

class AlteraDevice(Device):...

class Altera(BuildConfig):

    def _CheckPartCmd(self):
        if shutil.which('quartus_sh') == None:
            return None

        subproc = subprocess.Popen(
            args=['quartus_sh', '--tcl_eval', 'get_part_list'],
            stdout=subprocess.PIPE,
            stderr=subprocess.DEVNULL,
            stdin=subprocess.DEVNULL
        )

        return subproc.stdout.read().decode().lower().strip().split(' ')


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