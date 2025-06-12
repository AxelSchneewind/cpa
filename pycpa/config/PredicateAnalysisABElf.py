from pycpa.analyses import PredAbsPrecision, PredAbsABECPA, IsBlockOperator
from pycpa.analyses import CompositeCPA
from pycpa.analyses import LocationCPA
from pycpa.analyses import StackCPA
from pycpa.analyses import ARGCPA
from pycpa.analyses import ValueAnalysisCPA

import pprint

"""
Configuration for running Predicate Analysis with ABE and 
abstraction at branches and calls.
"""

def get_cpas(entry_point=None, cfa_roots=None, output_dir=None, **params):
    assert entry_point

    if cfa_roots is None:
        cfa_roots = [entry_point]
    precision = PredAbsPrecision.from_cfa(cfa_roots)

    # dump initial precision
    if output_dir:
        with open(output_dir + 'precision_initial.txt', 'w') as f:
            f.write(precision.__str__())

    return [StackCPA(CompositeCPA([LocationCPA(entry_point), PredAbsABECPA(precision, IsBlockOperator.is_block_head_lf)]))]

