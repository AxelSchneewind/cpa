from pycpa.analyses import PredAbsABEPrecision, PredAbsABECPA
from pycpa.analyses import CompositeCPA
from pycpa.analyses import LocationCPA
from pycpa.analyses import StackCPA
from pycpa.analyses import ARGCPA
from pycpa.analyses import ValueAnalysisCPA

import pprint

"""
Configuration for running Predicate Analysis with ABE and 
abstraction only at calls.
"""

def get_cpas(entry_point=None, cfa_roots=None, output_dir=None, **params):
    assert entry_point

    if cfa_roots is None:
        cfa_roots = [entry_point]
    precision = PredAbsABEPrecision.from_cfa(cfa_roots, PredAbsABEPrecision.is_block_head_f)

    # dump initial precision
    if output_dir:
        with open(output_dir + 'precision_initial.txt', 'w') as f:
            f.write(precision.__str__())

    return [StackCPA(CompositeCPA([LocationCPA(entry_point), PredAbsABECPA(precision, PredAbsABEPrecision.is_block_head_f)]))]

