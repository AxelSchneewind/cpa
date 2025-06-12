from pycpa.analyses import PredAbsPrecision, PredAbsCPA, PredAbsTransferRelation
from pycpa.analyses import CompositeCPA
from pycpa.analyses import LocationCPA
from pycpa.analyses import StackCPA
from pycpa.analyses import ARGCPA, ARGState
from pycpa.analyses import ValueAnalysisCPA


import pprint

from pycpa.cpa import CPA
from pycpa.task import Task, Result, Status
from pycpa.verdict import Verdict


from pycpa.cpaalgorithm import CPAAlgorithm

from pycpa.analyses.PredAbsCEGAR import PredAbsCEGARDriver
from pycpa.analyses import IsBlockOperator


# for now, this module is a special case where the cpa is not set up by the main function
def get_cpas(entry_point, **params):
    return []

# set up cegar driver here and use it as the algorithm
def get_algorithm(entrypoint, cfa_roots, specification, task : Task, result : Result):
    return PredAbsCEGARDriver(
        entrypoint,
        cfa_roots,
        task,
        result,
        specification,
        task.max_refinements,
        None,
        abe_blk=IsBlockOperator.is_block_head_lf
    )

