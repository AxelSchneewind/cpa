from pycpa.analyses import CompositeCPA
from pycpa.analyses import LocationCPA
from pycpa.analyses import ARGCPA
from pycpa.analyses import ValueAnalysisCPA

def get_cpas(cfa_root):
    return [LocationCPA(cfa_root), ValueAnalysisCPA()]
