import logging

ERR_PLDUDE_SUCCESS : int = 0
ERR_PLDUDE_FERROR  : int = 1
ERR_PLDUDE_PROJERR : int = 2
ERR_PLDUDE_PLATERR : int = 3
ERR_PLDUDE_VERBOSE : int = 4
ERR_PLDUDE_TOOLERR : int = 5
ERR_PLDUDE_TDEVERR : int = 6
ERR_PLDUDE_PINPERR : int = 7
ERR_PLDUDE_SYSTERR : int = 8
ERR_PLDUDE_MODFERR : int = 9

class PLDudeError(Exception):
    def __init__(self, err : str, exitcode : int, level : int = logging.CRITICAL):
        self.reason = err
        self.ecode = exitcode
        self.level = level

class PLPlatError(PLDudeError):
    def __init__(self, err : str):
        super().__init__(err=err, exitcode=ERR_PLDUDE_PLATERR)