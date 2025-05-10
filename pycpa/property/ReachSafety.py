
from pycpa.analyses import PropertyCPA, PropertyState, CompositeState, ARGState


def get_cpas():
    return [PropertyCPA()]


def state_property(state):
    if isinstance(state, CompositeState):
        for wrapped in state.wrapped_states:
            if isinstance(wrapped, PropertyState):
                return wrapped.safe == True
    elif isinstance(state, ARGState):
        return state_property(state.wrapped_state)
    else:
        raise NotImplementedError(state)
    
    return None

