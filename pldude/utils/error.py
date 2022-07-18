class PLDudeError(Exception):
    def __init__(self, msg : str):
        self.message = msg