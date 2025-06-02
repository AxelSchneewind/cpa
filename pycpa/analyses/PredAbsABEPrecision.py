#!/usr/bin/env python3
"""
    Predicate Abstraction Precision with large block encoding
"""

from __future__ import annotations

import ast, hashlib
import copy
from typing import Dict, Iterable, Set, List, Callable

from pysmt.typing  import BV64, BOOL
from pysmt.fnode   import FNode

from pycpa.analyses import PredAbsPrecision

from pycpa.cfa import CFANode, CFAEdge, InstructionType

from pycpa.analyses.ssa_helper import SSA


class IsBlockOperator:
    @staticmethod
    def is_block_head_fl(node: CFANode, edge : CFAEdge) -> bool:
        """branches and calls are block heads
        """
        kind = edge.instruction.kind
        match kind:
            case InstructionType.CALL | InstructionType.RETURN | InstructionType.ASSUMPTION:
                return True
            case _:
                # TODO: check for loop
                pass
        return False

    @staticmethod
    def is_block_head_f(node: CFANode, edge : CFAEdge) -> bool:
        """calls and returns are block heads
        """
        kind = edge.instruction.kind
        match kind:
            case InstructionType.CALL | InstructionType.RETURN:
                return True
            case _:
                pass
        return False

    @staticmethod
    def is_block_head_bf(node: CFANode, edge : CFAEdge) -> bool:
        """branches and calls are block heads
        """
        kind = edge.instruction.kind
        match kind:
            case InstructionType.CALL | InstructionType.RETURN | InstructionType.ASSUMPTION:
                return True
            case _:
                pass
        return False
