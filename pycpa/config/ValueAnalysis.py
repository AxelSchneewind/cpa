from pycpa.analyses import CompositeCPA
from pycpa.analyses import LocationCPA
from pycpa.analyses import StackCPA
from pycpa.analyses import ARGCPA
from pycpa.analyses import ValueAnalysisCPA

def get_cpas(entry_point=None, **params):
    assert entry_point
    return [StackCPA(CompositeCPA([LocationCPA(entry_point), ValueAnalysisCPA()]))]
