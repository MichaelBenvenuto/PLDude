import os
import sys
import logging
import re
import subprocess

from typing import Union, IO

from .__buildconfig import *
from pldude.utils.__utils import Device, PLDudeError

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
                    self._logging.info(vivado_match.group(3).strip(), extra={'synth_param' : vivado_param})
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