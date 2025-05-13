from pycpa.analyses import ARGCPA, ARGState
from pycpa.cpa import WrappedAbstractState, CPA
from pycpa.verdict import Verdict

from typing import Collection

class ARGVisitor:
    def _walk_arg(self, root : ARGState):
        yield root
        for c in root.children:
            for d in self._walk_arg(c):
                yield d

    def visit(self, root : ARGState):
        for n in self._walk_arg(root):
            self.visit_cpas(n)
        return self

    def visit_cpas(self, state):
        t = type(state).__name__
        func = 'visit_' + str(t)

        if hasattr(self, func):
            getattr(self, func)(state)
        else:
            underlying = WrappedAbstractState.unwrap(state)
            for c in WrappedAbstractState.unwrap(state):
                if c is not state:
                    self.visit_cpas(c)

    def get_verdict(self) -> Verdict:
        raise NotImplementedError()


class Specification:
    def get_cpas(self) -> Collection[CPA]:
        raise NotImplementedError()

    def get_state_visitor(self) -> ARGVisitor:
        raise NotImplementedError()

