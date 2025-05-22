from pycpa.analyses import PredAbsPrecisionABE, PredAbsCPA
from pycpa.analyses import CompositeCPA
from pycpa.analyses import LocationCPA
from pycpa.analyses import StackCPA
from pycpa.analyses import ARGCPA
from pycpa.analyses import ValueAnalysisCPA

import pprint

def get_cpas(entry_point=None, cfa_roots=None, output_dir=None, **params):
    assert entry_point

    if cfa_roots is None:
        cfa_roots = [entry_point]
    precision = PredAbsPrecisionABE.from_cfa(cfa_roots, PredAbsPrecisionABE.is_block_head_bf)

    # dump initial precision
    if output_dir:
        with open(output_dir + 'precision_initial.txt', 'w') as f:
            f.write(pprint.pformat(precision.predicates))

    return [StackCPA(CompositeCPA([LocationCPA(entry_point), PredAbsCPA(precision)]))]

