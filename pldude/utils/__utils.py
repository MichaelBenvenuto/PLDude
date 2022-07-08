import logging

class PLDudeError(Exception):
    def __init__(self, err : str, exitcode : int, level : int = logging.CRITICAL):
        self.reason = err
        self.ecode = exitcode
        self.level = level

class Device():...

class RepFile():
    def __init__(self, dir : str, type : str):
        self.dir = dir
        self.type = type

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