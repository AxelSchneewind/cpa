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


class TraverseCFA:
    @staticmethod
    def bfs(root: CFANode):
        waitlist : set[CFANode] = set()
        waitlist.add(root)

        while len(waitlist) > 0:
            n = waitlist.pop()
            yield n

            # collect successors
            waitlist.update({e.successor for e in n.leaving_edges})
            


class IsBlockOperator:
    @staticmethod
    def is_loop_head(root : CFANode) -> bool:
        """
            Perform BFS to check if given node can be reached again
        """
        root_seen = 0
        for n in TraverseCFA.bfs(root):
            if n == root:
                root_seen += 1

            # found node with smaller location, therefore root is not loop head
            if n.node_id < root.node_id:
                return False
            
        # check if root has been seen more than once
        return root_seen > 1
            
    @staticmethod
    def is_block_head_lf(node: CFANode, edge: CFAEdge) -> bool:
        """loop heads and calls are block heads"""
        kind = edge.instruction.kind
        match kind:
            case InstructionType.CALL | InstructionType.RETURN:
                return True
            case InstructionType.ASSUMPTION:
                return IsBlockOperator.is_loop_head(node)
        return False

    @staticmethod
    def is_block_head_f(node: CFANode, edge: CFAEdge) -> bool:
        """calls and returns are block heads"""
        kind = edge.instruction.kind
        match kind:
            case InstructionType.CALL | InstructionType.RETURN:
                return True
            case _:
                pass
        return False

    @staticmethod
    def is_block_head_bf(node: CFANode, edge: CFAEdge) -> bool:
        """branches and calls are block heads"""
        kind = edge.instruction.kind
        match kind:
            case InstructionType.CALL | InstructionType.RETURN | InstructionType.ASSUMPTION:
                return True
            case _:
                pass
        return False
