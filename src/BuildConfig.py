class BuildConfig:
    def __init__(self, config_stream : dict):
        self.config_stream = config_stream

    def GetFileType(self):
        ft = self.config_stream['filetype']
        if ft is None:
            print("Cannot use null filetype!")
            exit(3)
        return ft

    def GetTopMod(self):
        top = self.config_stream['top']
        if top is None:
            print("Cannot use null top module!")
            exit(4)
        return top

    def GetDevice(self):
        dev = self.config_stream['device']
        if dev is None:
            print("Cannot have null device!")
            exit(5)
        return dev

    def GetOptMode(self):
        print("Cannot use abstract build config...")

    def GetOptLevel(self):
        print("Cannot use abstract build config...")