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


class BlockEncodings:
    @staticmethod
    def is_block_head_fl(node: CFANode) -> bool:
        """branches and calls are block heads
        """
        for edge in node.leaving_edges:
            kind = edge.instruction.kind
            match kind:
                case InstructionType.CALL:
                    return True
                case _:
                    # TODO: check for loop
                    pass
        for edge in node.entering_edges:
            kind = edge.instruction.kind
            match kind:
                case InstructionType.RETURN:
                    return True
        return False

    @staticmethod
    def is_block_head_f(node: CFANode) -> bool:
        """branches and calls are block heads
        """
        for edge in node.leaving_edges:
            kind = edge.instruction.kind
            match kind:
                case InstructionType.CALL:
                    return True
        for edge in node.entering_edges:
            kind = edge.instruction.kind
            match kind:
                case InstructionType.RETURN:
                    return True
        return False

    @staticmethod
    def is_block_head_bf(node: CFANode) -> bool:
        """branches and calls are block heads
        """
        for edge in node.leaving_edges:
            kind = edge.instruction.kind
            match kind:
                case InstructionType.ASSUMPTION | InstructionType.CALL:
                    return True
                case _:
                    pass
        for edge in node.entering_edges:
            kind = edge.instruction.kind
            match kind:
                case InstructionType.RETURN:
                    return True
        return False




# --------------------------------------------------------------------------- #
#  Precision object                                                           #
# --------------------------------------------------------------------------- #
class PredAbsABEPrecision(Dict, Iterable):
    def __init__(self, preds: dict[CFANode,FNode], is_block_head : Callable[[CFANode], bool]):
        self.predicates: dict[CFANode,FNode] = preds
        self.is_block_head  = is_block_head

    def __getitem__(self, loc):  
        return self.predicates[loc]
    def __contains__(self, loc): 
        return loc in self.predicates

    def __iter__(self): 
        return iter(self.predicates)
    def __len__(self): 
        return len(self.predicates)

    def __str__(self):
        return str({ str(n) : str(p) for n,p in self.predicates.items()})


    def get_predicates_for_location(self, location: CFANode) -> set[FNode]:
        """
        Retrieves all applicable predicates for a given CFA node
        """
        assert location in self.predicates
        return self.predicates[location]

    def __getitem__(self, location: CFANode) -> set[FNode]:
        """Allows dictionary-like access, e.g., precision[cfa_node]."""
        assert location in self.predicates
        return self.predicates[location]


    def add_global_predicates(self, new_preds: Iterable[FNode]):
        """Adds new global predicates. Predicates are unindexed before storing."""
        for p in new_preds:
            self.global_predicates.add(SSA.unindex_predicate(p))

    def add_local_predicates(self, new_preds: dict[CFANode, Iterable[FNode]]):
        """Adds new predicates to location. SSA-indices have to be made relative to last block head before storing."""
        # TODO
        for location, preds in new_preds.items():
            if loc_node not in self.predicates:
                self.predicates[location] = set()

            for p in preds:
                self.predicates[location].add(SSA.unindex_predicate(p))

    @staticmethod
    def from_cfa(roots: list[CFANode], is_block_head : Callable[[CFANode], bool]) -> 'PredAbsABEPrecision':
        preds: dict[CFANode, set[FNode]] = { r : set() for r in roots }
        ssa_indices: dict[CFANode, dict[str,int]] = { r : {} for r in roots }
        todo, seen = list(roots), set()
        while todo:
            n = todo.pop()
            if n in seen: continue
            seen.add(n)

            is_head = is_block_head(n)

            for e in n.leaving_edges:
                # if not new block, copy current predicates to successor, otherwise keep empty set
                if e.successor not in preds:
                    preds[e.successor] = set()
                    ssa_indices[e.successor] = {}
                # use predicates and ssa_indices of parent
                if not is_head:
                    # TODO: ssa_index equalization
                    preds[e.successor].update(preds[n])
                    ssa_indices[e.successor].update(ssa_indices[n])

                f = PredAbsPrecision.from_cfa_edge(e, ssa_indices[e.successor])
                if f is not None and f.get_type().is_bool_type():
                    preds[e.successor].update(set(f.get_atoms()))
                todo.append(e.successor)

        return PredAbsABEPrecision(preds, is_block_head)
    
