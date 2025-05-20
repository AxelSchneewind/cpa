#!/usr/bin/env python
"""
Predicate-abstraction CPA with Cartesian abstraction and SSA support.
"""

from __future__ import annotations
import copy
import ast
import sys
from typing import List, Set, Dict

from pysmt.shortcuts import And, Not, TRUE, FALSE, is_sat
import pysmt.fnode as fnode
from pysmt.exceptions import SolverReturnedUnknownResultError

from pycpa.cfa import InstructionType, CFAEdge
from pycpa.cpa import CPA, AbstractState, TransferRelation, StopSepOperator, MergeSepOperator

from pycpa.analyses.PredAbsPrecision import PredAbsPrecision

# --------------------------------------------------------------------------- #
# Abstract State
# --------------------------------------------------------------------------- #
class PredAbsState(AbstractState):
    def __init__(self, other: PredAbsState | None = None) -> None:
        if other:
            self.predicates: Set[fnode.FNode] = set(other.predicates)
            self.ssa_indices: Dict[str, int] = copy.deepcopy(other.ssa_indices)
        else:
            self.predicates = set()
            self.ssa_indices = {}

    def subsumes(self, other: PredAbsState) -> bool:
        return other.predicates.issubset(self.predicates)

    def __eq__(self, other: object) -> bool:
        return (
            isinstance(other, PredAbsState) and
            self.predicates == other.predicates and
            self.ssa_indices == other.ssa_indices
        )

    def __hash__(self) -> int:
        return hash(frozenset(self.predicates)) ^ hash(frozenset(self.ssa_indices.items()))

    def __str__(self) -> str:
        return '{' + ', '.join(str(p) for p in self.predicates) + '}'

# --------------------------------------------------------------------------- #
# Transfer Relation
# --------------------------------------------------------------------------- #
class PredAbsTransferRelation(TransferRelation):
    """
    Cartesian abstraction:
      succ.predicates = { t ∈ π |  SP(edge, ∧preds(pre)) ⇒ t }
    """
    def __init__(self, precision: Set[fnode.FNode]) -> None:
        self.precision = precision

    @staticmethod
    def _implied_predicates(ctx: Set[fnode.FNode],
                            trans: fnode.FNode,
                            precision: Set[fnode.FNode]) -> Set[fnode.FNode]:
        phi = And(list(ctx)) if ctx else TRUE()
        phi = And(phi, trans)

        implied: Set[fnode.FNode] = set()
        for p in precision:
            try:
                sat = is_sat(And(phi, Not(p)))
            except SolverReturnedUnknownResultError:
                sat = True
            if not sat:                 # UNSAT ⇒ φ ⇒ p
                implied.add(p)
        
        # ------------------------------------------------------------ #
        #  VERBOSE LOGGING – print each *new* predicate set once
        # ------------------------------------------------------------ #
        # WTF
        main = sys.modules.get("__main__")
        if getattr(main, "args", None) and getattr(main.args, "verbose", False):
            seen = getattr(PredAbsCPA, "_seen_predsets", set())
            key  = frozenset(implied)
            if key not in seen:
                seen.add(key)
                PredAbsCPA._seen_predsets = seen
                print("New predicate set:", '{' + ', '.join(map(str, implied)) + '}')
        # ------------------------------------------------------------ #

        return implied

    def get_abstract_successors(self, predecessor: PredAbsState) -> List[PredAbsState]:
        raise NotImplementedError

    def get_abstract_successors_for_edge(self,
                                         predecessor: PredAbsState,
                                         edge: CFAEdge
                                        ) -> List[PredAbsState]:
        # 1) Copy SSA indices locally
        ssa_idx = copy.deepcopy(predecessor.ssa_indices)

        # 2) Compute strongest‐post condition (trans)
        kind = edge.instruction.kind
        if   kind == InstructionType.STATEMENT:
            trans = PredAbsPrecision.ssa_from_assign(edge, ssa_indices=ssa_idx)
        elif kind == InstructionType.ASSUMPTION:
            expr = PredAbsPrecision.ssa_from_assume(edge, ssa_indices=predecessor.ssa_indices)      # use old ssa_indices to not interfere with new state
            if not is_sat(And(expr, And(predecessor.predicates))):
                return []
            trans = PredAbsPrecision.ssa_from_assume(edge, ssa_indices=ssa_idx)
        elif kind == InstructionType.CALL:
            trans = PredAbsPrecision.ssa_from_call(edge, ssa_indices=ssa_idx)
        elif kind == InstructionType.REACH_ERROR:
            # **special case**: hitting an error-edge → FALSE
            trans = FALSE()
        else:
            trans = TRUE()

        # 3) If this is truly unsatisfiable (i.e. error-edge), preserve it
        if trans.is_false():
            succ = PredAbsState()
            succ.ssa_indices = ssa_idx
            succ.predicates  = {trans}
            return [succ]

        # 4) Otherwise do Cartesian abstraction
        new_preds = self._implied_predicates(
            predecessor.predicates,
            trans,
            self.precision
        )
        succ = PredAbsState()
        succ.ssa_indices = ssa_idx
        succ.predicates  = new_preds
        return [succ]

# --------------------------------------------------------------------------- #
# CPA wrapper
# --------------------------------------------------------------------------- #
class PredAbsCPA(CPA):
    def __init__(self, initial_precision) -> None:
        self.precision = (
            initial_precision.predicates
            if hasattr(initial_precision, "predicates")
            else set(initial_precision)
        )

    def get_initial_state(self) -> PredAbsState:
        return PredAbsState()

    def get_stop_operator(self) -> StopSepOperator:
        return StopSepOperator(PredAbsState.subsumes)

    def get_merge_operator(self) -> MergeSepOperator:
        return MergeSepOperator()

    def get_transfer_relation(self) -> TransferRelation:
        return PredAbsTransferRelation(self.precision)


