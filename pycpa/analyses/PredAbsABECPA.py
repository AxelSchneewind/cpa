#!/usr/bin/env python
"""
Predicate-abstraction CPA with Cartesian abstraction and SSA support.
"""

from __future__ import annotations
import copy
import ast
import sys
from typing import List, Set, Dict, Callable

from pysmt.shortcuts import And, Or, Not, is_sat, TRUE
from pysmt.fnode import FNode

from pycpa.cfa import InstructionType, CFAEdge, CFANode
from pycpa.cpa import ( 
    CPA, AbstractState, TransferRelation, StopSepOperator, MergeSepOperator, MergeOperator, StopOperator
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
            predicates: set[FNode],
            abstraction_location : CFANode | None,
            path_formula : FNode,
            path_ssa_indices: dict[str, int]):
        self.predicates = predicates
        self.abstraction_location = abstraction_location
        self.path_formula = path_formula
        self.path_ssa_indices = path_ssa_indices

    def _instantiate(self) -> FNode:
        preds = SSA.set_indices(And(list(self.predicates)), 0)
        return And(preds, self.path_formula)

    def subsumes(self, other: PredAbsABEState) -> bool:
        lformula = SSA.pad_indices(self._instantiate(),  self.path_ssa_indices, other.path_ssa_indices)
        rformula = SSA.pad_indices(other._instantiate(), other.path_ssa_indices, self.path_ssa_indices)

        # check implication of path formulas (self=>other)
        return (
            # self => other
            not is_sat(
                And(lformula, Not(rformula))
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

    def __copy__(self):
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
    def __init__(self, precision: PredAbsPrecision, block_heads : set[CFANode]) -> None:
        self.precision = precision
        self.block_heads = block_heads

    def get_abstract_successors(self, predecessor: AbstractState) -> List[PredAbsABEState]:
        raise NotImplementedError

    def get_abstract_successors_for_edge(self,
                                         predecessor: AbstractState,
                                         edge: CFAEdge
                                        ) -> List[PredAbsABEState]:
        assert isinstance(predecessor, PredAbsABEState)
        assert isinstance(edge, CFAEdge)

        # copy SSA indices locally, these will be advanced by the current edge formula
        ssa_idx = copy.copy(predecessor.path_ssa_indices)
        predicates = predecessor.predicates
        abstraction_location = predecessor.abstraction_location

        # check if successor node is head
        is_block_head = edge.predecessor in self.block_heads

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

            # reset path formula and ssa indices
            path_formula = TRUE()
            ssa_idx = dict()
        else:                   # update path formula
            # update path formula with current edge
            path_formula = And(predecessor.path_formula, trans)

        return [ PredAbsABEState(
            predicates,
            abstraction_location,
            path_formula,
            ssa_idx
        ) ]


class MergeJoinOperator(MergeOperator[PredAbsABEState]):
    def merge(self, e: PredAbsABEState, eprime: PredAbsABEState) -> PredAbsABEState:
        # can't merge if abstractions sets/locations differ
        if ( e.abstraction_location != eprime.abstraction_location
             or e.predicates != eprime.predicates):
            return eprime

        # take disjunction of path formulas
        e_path  = SSA.pad_indices(e.path_formula, e.path_ssa_indices, eprime.path_ssa_indices)
        ep_path = SSA.pad_indices(eprime.path_formula, eprime.path_ssa_indices, e.path_ssa_indices)
        result = copy.copy(eprime)
        result.path_formula = Or(e_path, ep_path)
        return result


# --------------------------------------------------------------------------- #
# CPA wrapper
# --------------------------------------------------------------------------- #
class PredAbsABECPA(CPA[PredAbsABEState]):
    def __init__(self, initial_precision : PredAbsPrecision, block_heads : set[CFANode]):
        self.precision = initial_precision
        self.block_heads = block_heads

    def get_initial_state(self) -> PredAbsABEState:
        return PredAbsABEState(
            set(),
            None,
            TRUE(),
            dict()
        )

    def get_stop_operator(self) -> StopOperator[PredAbsABEState]:
        return StopSepOperator(PredAbsABEState.subsumes)

    def get_merge_operator(self) -> MergeOperator[PredAbsABEState]:
        return MergeSepOperator()

    def get_transfer_relation(self) -> TransferRelation[PredAbsABEState]:
        return PredAbsABETransferRelation(self.precision, self.block_heads)


