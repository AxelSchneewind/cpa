from pycpa.analyses import PredAbsPrecision
from pycpa.analyses import CompositeCPA
from pycpa.analyses import LocationCPA
from pycpa.analyses import StackCPA
from pycpa.analyses import ARGCPA
from pycpa.analyses import ValueAnalysisCPA

def get_cpas(entry_point, cfa_roots=None, output_dir=None, **params):
    if cfa_roots is None:
        cfa_roots = [entry_point]
    precision = PredAbsPrecision.from_cfa(cfa_roots)

    # dump initial precision
    if output_dir:
        with open(output_dir + 'precision_initial.txt', 'w') as f:
            f.write(str(precision))

    # return [StackCPA(CompositeCPA([LocationCPA(entry_point), PredAbsCPA(precision)]))]
    return [StackCPA(CompositeCPA([LocationCPA(entry_point)]))]

