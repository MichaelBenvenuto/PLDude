import logging

class PLDudeError(Exception):
    def __init__(self, err : str, exitcode : int, level : int = logging.CRITICAL):
        self.reason = err
        self.ecode = exitcode
        self.level = level