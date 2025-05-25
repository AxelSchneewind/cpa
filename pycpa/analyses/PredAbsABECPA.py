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
from pycpa.analyses.PredAbsCPA import PredAbsCPA, PredAbsTransferRelation

# --------------------------------------------------------------------------- #
# Abstract State
# --------------------------------------------------------------------------- #
class PredAbsABEState(AbstractState):
    def __init__(self, other: PredAbsABEState | None = None) -> None:
        if other:
            self.predicates: Set[FNode] = set(other.predicates)
            self.ssa_indices: Dict[str, int] = copy.deepcopy(other.ssa_indices)
            self.path_formula : FNode = copy.copy(other.path_formula)
            self.path_ssa_indices: Dict[str, int] = copy.deepcopy(other.path_ssa_indices)
        else:
            # predicates computed at last block head
            self.predicates = set()
            # ssa indices at last block head
            self.ssa_indices = dict()
            # path formula since last block head
            self.path_formula : FNode = TRUE()
            # current ssa_indices
            self.path_ssa_indices: Dict[str, int] = dict()

    def subsumes(self, other: PredAbsABEState) -> bool:
        # check subset relation of predicates and implication of path formulas (self=>other)
        lformula = PredAbsPrecision.ssa_inc_indices(And(self.predicates), self.ssa_indices)
        rformula = PredAbsPrecision.ssa_inc_indices(And(other.predicates), other.ssa_indices)
        result = (
            # self => other
            not is_sat(
                And(And(self.path_formula, lformula), Not(And(other.path_formula, rformula)))
            )
        )

    def __eq__(self, other: object) -> bool:
        return (
            isinstance(other, PredAbsABEState) and
            self.predicates == other.predicates and
            self.ssa_indices == other.ssa_indices and
            self.path_formula == other.path_formula
        )

    def __hash__(self) -> int:
        return (frozenset(self.predicates).__hash__(), frozenset(self.ssa_indices.items()).__hash__(), self.path_formula.__hash__()).__hash__()

    def __str__(self) -> str:
        return '{' + ', '.join(str(p) for p in self.predicates) + '} | ' + str(self.path_formula)
    
    def __deepcopy__(self, memo):
        return PredAbsABEState(self)


# --------------------------------------------------------------------------- #
# Transfer Relation
# --------------------------------------------------------------------------- #
class PredAbsABETransferRelation(TransferRelation):
    """
    """
    def __init__(self, precision: PredAbsPrecisionABE, is_block_head) -> None:
        self.precision = precision
        self.is_block_head = is_block_head

    def get_abstract_successors(self, predecessor: PredAbsABEState) -> List[PredAbsABEState]:
        raise NotImplementedError

    def get_abstract_successors_for_edge(self,
                                         predecessor: PredAbsABEState,
                                         edge: CFAEdge
                                        ) -> List[PredAbsABEState]:
        # 1) Copy SSA indices locally, these will be advanced by the current edge formula
        ssa_idx = copy.deepcopy(predecessor.path_ssa_indices)
        predicates = None

        # check if successor node is head
        is_block_head = self.is_block_head(edge.successor)

        kind = edge.instruction.kind
        if   kind == InstructionType.STATEMENT:
            trans = PredAbsPrecision.ssa_from_assign(edge, ssa_indices=ssa_idx)
        elif kind == InstructionType.ASSUMPTION:
            expr = PredAbsPrecision.ssa_from_assume(edge, ssa_indices=ssa_idx)

            predecessor_formula = PredAbsPrecision.ssa_inc_indices(And(predecessor.predicates), predecessor.ssa_indices)
            if not is_sat(And(And(expr, predecessor.path_formula), predecessor_formula)):
                return []

            trans = expr
        elif kind == InstructionType.CALL:
            trans = PredAbsPrecision.ssa_from_call(edge, ssa_indices=ssa_idx)
        elif kind == InstructionType.RESUME:
            # special case: incorporate formulas from function call
            # predicates = edge.instruction.stackframe.predicates
            trans = edge.instruction.stackframe.path_formula
            ssa_idx.update(edge.instruction.stackframe.ssa_indices)
        else:
            trans = TRUE()

        if is_block_head:
            # 3) If this is truly unsatisfiable (i.e. error-edge), preserve it
            if trans.is_false():
                succ = PredAbsABEState()
                succ.ssa_indices = ssa_idx
                succ.predicates  = {trans}
                return [succ]

            # 4) Otherwise do Cartesian abstraction
            predicates = PredAbsTransferRelation._implied_predicates(
                predecessor.predicates,
                And(predecessor.path_formula, trans),
                self.precision[edge.successor],
                predecessor.ssa_indices,
                ssa_idx
            )

            # reset path formula
            path_formula = TRUE()
        else:
            # update path formula with current edge
            path_formula = And(trans, predecessor.path_formula)
            # keep these from previous block head
            predicates   = predecessor.predicates


        succ = PredAbsABEState()
        succ.ssa_indices = ssa_idx if is_block_head else predecessor.ssa_indices
        succ.predicates  = predicates
        succ.path_formula = path_formula
        succ.path_ssa_indices = ssa_idx
        return [succ]

# --------------------------------------------------------------------------- #
# CPA wrapper
# --------------------------------------------------------------------------- #
class PredAbsABECPA(CPA):
    def __init__(self, initial_precision, is_block_head) -> None:
        self.precision = initial_precision
        self.is_block_head = is_block_head

    def get_initial_state(self) -> PredAbsABEState:
        return PredAbsABEState()

    def get_stop_operator(self) -> StopSepOperator:
        return StopSepOperator(PredAbsABEState.subsumes)

    def get_merge_operator(self) -> MergeSepOperator:
        return MergeSepOperator()

    def get_transfer_relation(self) -> TransferRelation:
        return PredAbsABETransferRelation(self.precision, self.is_block_head)


