

from typing import Collection

class Task:
    def __init__(self, program : str, configs : Collection[str] = [], properties : Collection[str] = [], max_iterations=None):
        self.program = program
        self.configs = configs
        self.properties = properties
        self.max_iterations = max_iterations
    
    def __str__(self):
        return '%s' % self.program

from enum import Enum

class Status(Enum):
    OK = 0,
    TIMEOUT = 1,
    OUT_OF_MEMORY = 2,
    ABORTED_BY_USER = 3,
    ERROR = 4

    def __str__(self):
        return Enum.__str__(self).replace('Verdict.', '')


from pycpa.verdict import Verdict

class Result:
    def __init__(self, verdict=Verdict.UNKNOWN, witness=None):
        self.arg_complete = False
        self.verdict = verdict
        self.witness = witness