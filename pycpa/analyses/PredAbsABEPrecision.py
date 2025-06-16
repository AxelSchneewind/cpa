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

from pycpa.cfa import CFANode, CFAEdge, InstructionType, TraverseCFA

from pycpa.analyses.ssa_helper import SSA



class IsBlockOperator:
    @staticmethod
    def is_loop_head(root : CFANode) -> bool:
        """
            Perform BFS to check if given node can be reached again
        """
        root_seen = 0
        for e in TraverseCFA.bfs_edges(root):
            if e.successor == root:
                return True

            # found node with smaller location, therefore root is not loop head
            if e.successor.node_id < root.node_id:
                return False
            
        # check if root has been seen more than once
        return root_seen > 1
            
    @staticmethod
    def is_block_head_lf(node : CFANode) -> bool:
        """loop heads and calls are block heads"""

        if len(node.entering_edges) == 0 or len(node.leaving_edges) == 0:
            return True

        if any(e.instruction.kind == InstructionType.CALL for e in node.leaving_edges):
            return True

        if IsBlockOperator.is_loop_head(node):
            return True

        return False

    @staticmethod
    def is_block_head_f(node : CFANode) -> bool:
        """calls and returns are block heads"""

        if len(node.entering_edges) == 0 or len(node.leaving_edges) == 0:
            return True

        if any(e.instruction.kind == InstructionType.CALL for e in node.leaving_edges):
            return True

        return False

    @staticmethod
    def is_block_head_bf(node : CFANode) -> bool:
        """branches and calls are block heads"""

        if len(node.entering_edges) == 0 or len(node.leaving_edges) == 0:
            return True

        if any(e.instruction.kind == InstructionType.CALL for e in node.leaving_edges):
            return True

        if any(e.instruction.kind == InstructionType.ASSUMPTION for e in node.leaving_edges):
            return True

        return False


def compute_block_heads(cfa_roots : set[CFANode], blk : Callable[[CFANode], bool]):
    heads = set()
    for r in cfa_roots:
        heads.update({ n for n in TraverseCFA.bfs(r) if blk(n) })
    return heads