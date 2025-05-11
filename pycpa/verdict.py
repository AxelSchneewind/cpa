
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
    
    def __str__(self):
        return Enum.__str__(self).replace('Verdict.', '')


def walk_arg(stack):
    node = stack.pop()
    for c in node.children:
        stack.append(c)
    yield node

def evaluate_arg_safety(arg_root, state_prop):
    stack = list()
    stack.append(arg_root)
    for node in walk_arg(stack):
        if state_prop(node) == False:
            return Verdict.FALSE
    
    return Verdict.TRUE
