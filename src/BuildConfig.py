import subprocess

from sys import exit

class BuildConfig:
    def __init__(self, config_stream : dict, pin_stream : dict):
        self.config_stream = config_stream
        self.pin_stream = pin_stream

    def GetFileType(self):
        if not 'filetype' in self.config_stream:
            return "mixed"
        ft = self.config_stream['filetype']
        if ft is None:
            print("Cannot use null filetype!")
            exit(3)
        return ft

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

    def GetPins(self):
        print("Cannot use abstract build config...")

    def GetOptMode(self):
        print("Cannot use abstract build config...")

    def GetOptLevel(self):
        print("Cannot use abstract build config...")

def process_handler(proc : subprocess):
    while True:
        return_code = proc.poll()
        output = proc.stdout.readline().decode("utf-8")
        if output is not '':
            print(output, end='')
        if return_code is not None:
            if return_code != 0:
                exit(return_code)
            break
    pass