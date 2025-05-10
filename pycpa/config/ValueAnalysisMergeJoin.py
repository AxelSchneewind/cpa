from pycpa.cpa import MergeJoinOperator
from pycpa.analyses import CompositeCPA
from pycpa.analyses import LocationCPA
from pycpa.analyses import ARGCPA
from pycpa.analyses import ValueAnalysisCPA


def get_cpa(cfa_root):
    ValueAnalysisCPA.get_merge_operator = lambda x: MergeJoinOperator()
    result = ARGCPA(CompositeCPA([LocationCPA(cfa_root), ValueAnalysisCPA()]))
    return result