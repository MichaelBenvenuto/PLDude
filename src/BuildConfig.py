import subprocess

from sys import *

class BuildConfig:
    def __init__(self, config_stream : dict, pin_stream : dict):
        self.config_stream = config_stream
        self.pin_stream = pin_stream

    def GetFileType(self):
        ft = self.config_stream.get("filetype", None)
        if ft is None:
            print("Warning! Null filetype, defaulting to \"mixed\"")
            return "mixed"
        return ft

    def GetTimingReport(self, stage : str):
        return stage in self.config_stream.get("timing_reports", [])

    def GetUtilizeReport(self, stage : str):
        return stage in self.config_stream.get("util_reports", [])

    def GetClockUtilize(self):
        return self.config_stream.get("clock_report", True)

    def GetTopMod(self):
        if not 'top' in self.config_stream:
            print("No top module specified in pldprj.yml!")
            exit(4)
        top = self.config_stream['top']
        if top is None:
            print("Cannot use null top module!")
            exit(4)
        return top

    def GetDevice(self):
        if not 'device' in self.config_stream:
            print("No device specified in pldprj.yml!")
            exit(5)
        dev = self.config_stream['device']
        if dev is None:
            print("Cannot have null device!")
            exit(5)
        return dev

    def GetDeviceNoPackage(self):
        print("Cannot use abstract function...")

    def GetSrcDir(self):
        if not 'src' in self.config_stream:
            return "./"
        src = self.config_stream['src']
        if src is None:
            print("Warning! Null src directory, defaulting to \"./\"")
            return "./"
        return src

    def GetDeviceDir(self):
        if not 'devsrc' in self.config_stream:
            return ""
        devsrc = self.config_stream['devsrc']
        if devsrc is None:
            print("Warning! Null devsrc directory, device-specific files will not be used.")
            return ""
        return devsrc

    def GetVHDL2008(self):
        return self.config_stream.get('vhdl_2008', False)

    def GetPins(self):
        print("Cannot use abstract build config...")

    def GetOptMode(self):
        print("Cannot use abstract build config...")

    def GetOptLevel(self):
        print("Cannot use abstract build config...")

    def Run(self, files, program, only_program, simulate, simulate_arg, verbose):
        print("Cannot run abstract build config...")

def process_handler(proc : subprocess, verbose : bool, file):
    data = proc.communicate()
    if file is not None:
        file.write(data[0].decode().replace('\r', ''))
    if verbose and data[0] is not None:
        print(data[0].decode().replace('\r', ''))
    if data[1] is not None:
        print(data[1].decode().replace('\r', ''))