from pycpa.analyses import CompositeCPA
from pycpa.analyses import LocationCPA
from pycpa.analyses import StackCPA
from pycpa.analyses import ARGCPA
from pycpa.analyses import ValueAnalysisCPA, ValueState

from pycpa.cpa import MergeOperator, AbstractState

class ValueMergeJoinOperator(MergeOperator[ValueState]):
    def merge(self, e: ValueState, eprime: ValueState) -> ValueState:
        for k,v in e.valuation.items():
            if k in eprime.valuation and v != eprime.valuation[k]:
                eprime.valuation.pop(k)

        return eprime

def get_cpas(entry_point=None, **params):
    assert entry_point
    ValueAnalysisCPA.get_merge_operator = lambda x: ValueMergeJoinOperator()
    return [StackCPA(CompositeCPA([LocationCPA(entry_point), ValueAnalysisCPA()]))]
