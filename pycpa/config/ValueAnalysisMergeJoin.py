from pycpa.cpa import MergeJoinOperator
from pycpa.analyses import CompositeCPA
from pycpa.analyses import LocationCPA
from pycpa.analyses import StackCPA
from pycpa.analyses import ARGCPA
from pycpa.analyses import ValueAnalysisCPA


def get_cpas(entry_point, **params):
    ValueAnalysisCPA.get_merge_operator = lambda x: MergeJoinOperator()
    return [StackCPA(CompositeCPA([LocationCPA(entry_point), ValueAnalysisCPA()]))]
