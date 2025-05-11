
from enum import Enum
class Verdict(Enum):
    TRUE = 0,
    FALSE = 1,
    UNKNOWN = 2

    def __and__(self, other):
        if self == Verdict.TRUE:
            return other
        elif self == Verdict.FALSE:
            return self
        elif self == Verdict.UNKNOWN and other == Verdict.TRUE:
            return self
        elif self == Verdict.UNKNOWN and (other == Verdict.FALSE or other == Verdict.UNKNOWN):
            return other


def walk_arg(node):
    yield node
    for c in node.children:
        for d in walk_arg(c):
            yield d 

def evaluate_arg_safety(arg_root, state_prop):
    for node in walk_arg(arg_root):
        if state_prop(node) == False:
            return Verdict.FALSE
    
    return Verdict.TRUE
