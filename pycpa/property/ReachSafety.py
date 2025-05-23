
from pycpa.cpa import WrappedAbstractState
from pycpa.analyses import PropertyCPA, PropertyState, CompositeState

from pycpa.specification import Specification, ARGVisitor
from pycpa.verdict import Verdict

def get_cpas(**params):
    return [PropertyCPA()]

def check_arg_state(state):
    sr = Verdict.TRUE
    for s in WrappedAbstractState.get_substates(state, PropertyState):
        sr &= Verdict.TRUE if s.safe else Verdict.FALSE
    return sr

    
