#!/usr/bin/env python
"""
Predicate-abstraction CPA with Cartesian abstraction and SSA support.
"""

from __future__ import annotations
import copy
import ast
import sys
from typing import List, Set, Dict

from pysmt.shortcuts import And, Not, TRUE, FALSE, is_sat, Or
from pysmt.fnode import FNode
from pysmt.exceptions import SolverReturnedUnknownResultError

from pycpa.cfa import InstructionType, CFAEdge, CFANode
from pycpa.cpa import ( 
    CPA, AbstractState, TransferRelation, StopSepOperator, MergeSepOperator, MergeOperator
)


from pycpa.analyses.PredAbsPrecision import PredAbsPrecision
from pycpa.analyses.PredAbsCPA import PredAbsCPA, PredAbsTransferRelation

from pycpa.analyses.ssa_helper import SSA


import copy

# --------------------------------------------------------------------------- #
# Abstract State
# --------------------------------------------------------------------------- #
class PredAbsABEState(AbstractState):
    def __init__(self,
            predicates: Set[FNode],
            abstraction_location : CFANode,
            path_formula : FNode,
            path_ssa_indices: Dict[str, int]
    ) -> None:
        self.predicates = predicates
        self.abstraction_location = abstraction_location
        self.path_formula = path_formula
        self.path_ssa_indices = path_ssa_indices

    def subsumes(self, other: PredAbsABEState) -> bool:
        # check subset relation of predicates and implication of path formulas (self=>other)
        lformula = SSA.pad_indices(self.path_formula, self.path_ssa_indices, other.path_ssa_indices)
        rformula = SSA.pad_indices(other.path_formula, other.path_ssa_indices, self.path_ssa_indices)

        return (
            # self => other
            other.predicates.issubset(self.predicates) 
            and not is_sat(
                And(And(self.path_formula, lformula), Not(And(other.path_formula, rformula)))
            )
        )


    def __eq__(self, other: object) -> bool:
        return (
            isinstance(other, PredAbsABEState) and
            self.predicates == other.predicates and
            self.abstraction_location == other.abstraction_location and
            self.path_ssa_indices == other.path_ssa_indices and
            self.path_formula == other.path_formula
        )

    def __hash__(self) -> int:
        return (frozenset(self.predicates).__hash__(), self.abstraction_location.__hash__(), frozenset(self.path_ssa_indices.items()).__hash__(), self.path_formula.__hash__()).__hash__()

    def __str__(self) -> str:
        return '{' + ', '.join(str(p) for p in self.predicates) + '} | ' + str(self.path_formula)
    
    def __deepcopy__(self, memo):
        return PredAbsABEState(
            copy.copy(self.predicates),
            self.abstraction_location,
            copy.copy(self.path_formula),
            copy.copy(self.path_ssa_indices)
        )


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
        ssa_idx = copy.copy(predecessor.path_ssa_indices)
        predicates = None
        abstraction_location = predecessor.abstraction_location

        # check if successor node is head
        is_block_head = self.is_block_head(edge.predecessor, edge)

        kind = edge.instruction.kind
        if   kind == InstructionType.STATEMENT:
            trans = PredAbsPrecision.ssa_from_assign(edge, ssa_indices=ssa_idx)
        elif kind == InstructionType.ASSUMPTION:
            trans = PredAbsPrecision.ssa_from_assume(edge, ssa_indices=ssa_idx)

            predecessor_formula = SSA.set_indices(And(predecessor.predicates), predecessor.path_ssa_indices)
            if not is_sat(And(And(trans, predecessor.path_formula), predecessor_formula)):
                return []
        elif kind == InstructionType.CALL:
            trans = PredAbsPrecision.ssa_from_call(edge, ssa_indices=ssa_idx)
        elif kind == InstructionType.RETURN:
            trans = PredAbsPrecision.ssa_from_return_dynamic(edge, ssa_indices=ssa_idx)
        else:
            trans = TRUE()

        if is_block_head:       # compute new abstraction formula
            if And(predecessor.path_formula, trans).is_false():
                return []

            predicates = PredAbsTransferRelation._implied_predicates(
                predecessor.predicates,
                And(predecessor.path_formula, trans),
                self.precision[edge.successor],
                0,
                ssa_idx
            )
            predicates = { SSA.unindex_predicate(p) for p in predicates }

            # store location of new abstraction formula
            abstraction_location = edge.predecessor

            # reset path formula
            path_formula = TRUE()
            ssa_idx = dict()
        else:                   # update path formula
            # update path formula with current edge
            path_formula = And(trans, predecessor.path_formula)
            # keep these from previous block head
            predicates   = predecessor.predicates

        return [ PredAbsABEState(
            predicates,
            abstraction_location,
            path_formula,
            ssa_idx
        ) ]


class MergeJoinOperator(MergeOperator):
    def merge(self, e: PredAbsABEState, eprime: PredAbsABEState) -> AbstractState:
        # can't merge if different abstractions
        if ( e.abstraction_location != eprime.abstraction_location
             or e.predicates != eprime.predicates):
            return eprime
        
        eprime.path_formula = Or(SSA.pad_indices(e.path_formula, e.path_ssa_indices, eprime.path_ssa_indices), SSA.pad_indices(eprime.path_formula, eprime.path_ssa_indices, e.path_ssa_indices))
        return eprime


# --------------------------------------------------------------------------- #
# CPA wrapper
# --------------------------------------------------------------------------- #
class PredAbsABECPA(CPA):
    def __init__(self, initial_precision, is_block_head) -> None:
        self.precision = initial_precision
        self.is_block_head = is_block_head

    def get_initial_state(self) -> PredAbsABEState:
        return PredAbsABEState(
            set(),
            None,
            TRUE(),
            dict()
        )

    def get_stop_operator(self) -> StopSepOperator:
        return StopSepOperator(PredAbsABEState.subsumes)

    def get_merge_operator(self) -> MergeJoinOperator:
        return MergeJoinOperator()

    def get_transfer_relation(self) -> TransferRelation:
        return PredAbsABETransferRelation(self.precision, self.is_block_head)


