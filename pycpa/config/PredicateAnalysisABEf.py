from pycpa.analyses import PredAbsPrecision, PredAbsABECPA, IsBlockOperator, compute_block_heads
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
    precision = PredAbsPrecision.from_cfa(cfa_roots)

    # dump initial precision
    if output_dir:
        with open(output_dir + 'precision_initial.txt', 'w') as f:
            f.write(precision.__str__())

    heads = compute_block_heads(cfa_roots, IsBlockOperator.is_block_head_f)
    if output_dir:
        with open(output_dir + 'block_heads.txt', 'w') as f:
            f.write(str({ h.node_id for h in heads }))

    return [StackCPA(CompositeCPA([LocationCPA(entry_point), PredAbsABECPA(precision, heads)]))]

