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
from pysmt.fnode import FNode
from pysmt.exceptions import SolverReturnedUnknownResultError

from pycpa.cfa import InstructionType, CFAEdge
from pycpa.cpa import CPA, AbstractState, TransferRelation, StopSepOperator, MergeSepOperator

from pycpa.analyses.PredAbsPrecision import PredAbsPrecision

from pycpa.analyses.ssa_helper import SSA

# --------------------------------------------------------------------------- #
# Abstract State
# --------------------------------------------------------------------------- #
class PredAbsState(AbstractState):
    def __init__(self, other: PredAbsState | None = None) -> None:
        if other:   # copy constructor
            self.predicates: Set[FNode] = set(other.predicates)
            self.ssa_indices: Dict[str, int] = copy.deepcopy(other.ssa_indices)
        else:
            self.predicates = set()
            self.ssa_indices = dict()

    def subsumes(self, other: PredAbsState) -> bool:
        return other.predicates.issubset(self.predicates)

    def __eq__(self, other: object) -> bool:
        return (
            isinstance(other, PredAbsState) and
            self.predicates == other.predicates and
            self.ssa_indices == other.ssa_indices
        )

    def __hash__(self) -> int:
        return (frozenset(self.predicates).__hash__(), frozenset(self.ssa_indices.items()).__hash__()).__hash__()

    def __str__(self) -> str:
        return '{' + ', '.join(str(p) for p in self.predicates) + '}'
    
    def __deepcopy__(self, memo):
        return PredAbsState(self)


# --------------------------------------------------------------------------- #
# Transfer Relation
# --------------------------------------------------------------------------- #
class PredAbsTransferRelation(TransferRelation):
    """
    Cartesian abstraction:
      succ.predicates = { t ∈ π |  SP(edge, ∧preds(pre)) ⇒ t }
    """
    def __init__(self, precision: PredAbsPrecision | PredAbsPrecision) -> None:
        self.precision = precision

    @staticmethod
    def _implied_predicates(current_predicates: set[FNode],
                            transfer: FNode,
                            precision: set[FNode],
                            ssa_indices_old : dict[str,int],
                            ssa_indices_new : dict[str,int]) -> Set[FNode]:
        """
            computes predicates from the given precision
            that are implied from current predicates and (edge/path-formula) transfer.

            ssa_indices_old has to be the ssa indices before transfer formula.
            ssa_indices_new has to be the ssa indices after transfer formula.
        """
        phi = And(list(current_predicates)) if current_predicates else TRUE()
        phi = SSA.set_indices(phi, ssa_indices_old)
        phi = And(phi, transfer)

        implied: Set[FNode] = set()
        for p in precision:
            pnew = SSA.set_indices(p, ssa_indices_new)
            sat = is_sat(And(phi, Not(pnew)))
            if not sat:
                implied.add(SSA.unindex_predicate(pnew))

        return implied

    def get_abstract_successors(self, predecessor: PredAbsState) -> List[PredAbsState]:
        raise NotImplementedError()

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
            expr = PredAbsPrecision.ssa_from_assume(edge, ssa_indices=ssa_idx)

            predecessor_formula = SSA.set_indices(And(predecessor.predicates), predecessor.ssa_indices)
            if not is_sat(And(expr, predecessor_formula)):
                return []

            trans = expr
        elif kind == InstructionType.CALL or kind == InstructionType.NONDET:
            trans = PredAbsPrecision.ssa_from_call(edge, ssa_indices=ssa_idx)
        elif kind == InstructionType.RETURN:
            trans = PredAbsPrecision.ssa_from_return_dynamic(edge, ssa_indices=ssa_idx)
        else:
            trans = TRUE()

        # implication checks
        new_preds = self._implied_predicates(
            predecessor.predicates,
            trans,
            self.precision.get_predicates_for_location(edge.successor),
            predecessor.ssa_indices,
            ssa_idx
        )

        if FALSE() in new_preds:
            return []

        succ = PredAbsState()
        succ.ssa_indices = ssa_idx
        succ.predicates  = new_preds
        return [succ]

# --------------------------------------------------------------------------- #
# CPA wrapper
# --------------------------------------------------------------------------- #
class PredAbsCPA(CPA):
    def __init__(self, initial_precision) -> None:
        self.precision = initial_precision

    def get_initial_state(self) -> PredAbsState:
        return PredAbsState()

    def get_stop_operator(self) -> StopSepOperator:
        return StopSepOperator(PredAbsState.subsumes)

    def get_merge_operator(self) -> MergeSepOperator:
        return MergeSepOperator()

    def get_transfer_relation(self) -> TransferRelation:
        return PredAbsTransferRelation(self.precision)


