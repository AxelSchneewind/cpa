from pycpa.analyses import CompositeCPA
from pycpa.analyses import LocationCPA
from pycpa.analyses import StackCPA
from pycpa.analyses import ARGCPA
from pycpa.analyses import ValueAnalysisCPA

def get_cpas(cfa_root, **params):
    return [StackCPA(CompositeCPA([LocationCPA(cfa_root), ValueAnalysisCPA()]))]
