from pycpa.analyses import ARGCPA, ARGState
from pycpa.cpa import WrappedAbstractState, CPA
from pycpa.verdict import Verdict

from typing import Collection

class Specification:
    def get_cpas(self) -> Collection[CPA]:
        raise NotImplementedError()

    def check_arg_state(self, state) -> Verdict:
        raise NotImplementedError()

