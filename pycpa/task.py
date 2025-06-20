

from typing import Collection

from os import path


class Task:
    def __init__(self, program : str, args, configs : Collection[str] = [], properties : Collection[str] = []):
        # base name of program
        self.program = program
        self.program_name = program.split('/')[-1].split('.')[0]
        self.configs = configs
        self.properties = set(properties)
        self.max_iterations = args.max_iterations
        self.max_refinements = args.max_refinements
        self.output_directory = args.output_directory + '/' + self.program_name

    @staticmethod
    def task_from_args(program, base_dir, args):
        return Task(
            program,
            args,
            args.config,
            { path.splitext(path.basename(p))[0] for p in  args.property},
        )

    @staticmethod
    def task_from_yml(yml, base_dir, args):
        return Task(
                base_dir + '/' + yml['input_files'].split(' ')[0],  # only accept single program for now
                args,
                args.config,
                { p.split('/')[-1].split('.')[0] for p in  args.property},
        )
    
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
        return Enum.__str__(self).replace('Status.', '')


from pycpa.verdict import Verdict

class Result:
    def __init__(self, verdict=Verdict.UNKNOWN, witness=None):
        self.arg_complete = False
        self.verdict = verdict
        self.witness = witness
        self.status = Status.OK
