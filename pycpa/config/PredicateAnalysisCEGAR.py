from pycpa.analyses import PredAbsPrecision, PredAbsCPA, PredAbsTransferRelation
from pycpa.analyses import CompositeCPA
from pycpa.analyses import LocationCPA
from pycpa.analyses import StackCPA
from pycpa.analyses import ARGCPA, ARGState
from pycpa.analyses import ValueAnalysisCPA


import pprint

from pycpa.cpa import CPA, WrappedTransferRelation
from pycpa.task import Task, Result, Status
from pycpa.verdict import Verdict


from pycpa.cpaalgorithm import CPAAlgorithm

from pycpa.analyses.PredAbsCEGAR import _analyse_once, cegar_helper
from pycpa.analyses import PredAbsPrecision


# global variable, this is bad
precision = None

class CEGARCPAAlgorithm(CPAAlgorithm):
    def __init__(self, cpa, specifications, task : Task, result : Result):
        self.cpa = cpa
        self.iterations = 0
        self.task = task
        self.result = result
        self.specifications = specifications
        self.precision = precision

    def run(self, entry):
        return CPAAlgorithm.run(self, entry)

    @staticmethod
    def _make_cex_paths_rec(cpa, edge, specification, current=None):
        newpath = current + [edge] if current is not None else [edge]
        if specification.check_arg_state(edge.successor) == Verdict.UNSAFE:
            # reached unsafe
            yield newpath
        else:
            for ne in edge.successor.leaving_edges:
                yield _make_cex_paths_rec(cpa, ne, specification, newpath)
    
    def make_counterexample(self, init, unsafe_state):
        assert isinstance(init, ARGState)
        if not isinstance(unsafe_state, ARGState): 
            return None

        current = unsafe_state
        result = []
        while current is not init:
            parent = next((c for c in current.get_parents()), None)
            if parent is None:
                break
            edge = parent.get_edge(current)
            result.append(edge)
            current = parent

        result.reverse()
        if cegar_helper.is_path_feasible(result): return result
        
        return None

    def refine(self, cpa, counter_example) -> CPA:
        for relation in WrappedTransferRelation.get_subrelations(cpa.get_transfer_relation(), PredAbsTransferRelation):
            self.precision = cegar_helper.refine_precision(counter_example, precision)
            relation.precision = precision
        # print('precision ', self.precision)
        return cpa


def get_algorithm(cpa, specification, task : Task, result : Result ):
    return CEGARCPAAlgorithm(cpa, specification, task, result)

def get_cpas(entry_point=None, cfa_roots=None, output_dir=None, **params):
    assert entry_point
    global precision

    if cfa_roots is None:
        cfa_roots = [entry_point]
    precision = PredAbsPrecision.from_cfa(cfa_roots)

    # dump initial precision
    if output_dir:
        with open(output_dir + 'precision_initial.txt', 'w') as f:
            f.write(pprint.pformat(precision.predicates))

    return [StackCPA(CompositeCPA([LocationCPA(entry_point), PredAbsCPA(precision)]))]

