#!/usr/bin/env python3
"""
    Predicate Abstraction Precision with large block encoding
"""

import ast, hashlib
import copy
from typing import Dict, Iterable, Set, List, Callable

from pysmt.typing  import BV64, BOOL
from pysmt.fnode   import FNode

from pycpa.analyses import PredAbsPrecision

from pycpa.cfa import CFANode, CFAEdge, InstructionType

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

    @staticmethod
    def is_block_head_f(node: CFANode) -> bool:
        """branches and calls are block heads
        """
        for edge in node.leaving_edges:
            kind = edge.instruction.kind
            match kind:
                case InstructionType.CALL | InstructionType.RESUME:
                    return True
                case _:
                    pass
        return False

    @staticmethod
    def is_block_head_bf(node: CFANode) -> bool:
        """branches and calls are block heads
        """
        for edge in node.leaving_edges:
            kind = edge.instruction.kind
            match kind:
                case InstructionType.ASSUMPTION | InstructionType.CALL | InstructionType.RESUME:
                    return True
                case _:
                    pass
        return False

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
    