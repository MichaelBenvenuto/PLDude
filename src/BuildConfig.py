class BuildConfig:
    def __init__(self, config_stream : dict):
        self.file_type = config_stream['filetype']
        self.device = config_stream['device']
        self.top = config_stream['top']
        self.opt = config_stream['optimize']
