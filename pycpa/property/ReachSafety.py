
from pycpa.cpa import WrappedAbstractState
from pycpa.analyses import PropertyCPA, PropertyState, CompositeState

from pycpa.specification import Specification, ARGVisitor
from pycpa.verdict import Verdict

class ReachSafetyARGVisitor(ARGVisitor):
    def __init__(self):
        self.result = Verdict.TRUE

    def visit_PropertyState(self, state : PropertyState):
        sr = Verdict.TRUE if state.safe else Verdict.FALSE
        self.result &= sr
        
    def verdict(self) -> Verdict:
        return self.result

def get_cpas(**params):
    return [PropertyCPA()]

def check_arg_state(state):
    v = ReachSafetyARGVisitor()
    v.visit(state)
    return v.verdict()

    
