from pycpa.analyses import CompositeCPA
from pycpa.analyses import LocationCPA
from pycpa.analyses import ARGCPA
from pycpa.analyses import ValueAnalysisCPA

def get_cpa(cfa_root):
    return ARGCPA(CompositeCPA([LocationCPA(cfa_root), ValueAnalysisCPA()]))

