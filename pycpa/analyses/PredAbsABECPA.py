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

# --------------------------------------------------------------------------- #
# Abstract State
# --------------------------------------------------------------------------- #
class PredAbsABEState(AbstractState):
    def __init__(self, other: PredAbsABEState | None = None) -> None:
        if other:
            self.predicates: Set[FNode] = set(other.predicates)
            self.ssa_indices: Dict[str, int] = copy.deepcopy(other.ssa_indices)
            self.path_formula : FNode = copy.copy(other.path_formula)
        else:
            self.predicates = set()
            self.ssa_indices = dict()
            self.path_formula : FNode = TRUE()

    def subsumes(self, other: PredAbsABEState) -> bool:
        # check subset relation of predicates and implication of path formulas
        return other.predicates.issubset(self.predicates) and not is_sat(And(self.path_formula, Not(other.path_formula)))

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

    @staticmethod
    def _implied_predicates(ctx: Set[FNode],
                            trans: FNode,
                            precision: Set[FNode]) -> Set[FNode]:
        phi = And(list(ctx)) if ctx else TRUE()
        phi = And(phi, trans)

        implied: Set[FNode] = set()
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

    def get_abstract_successors(self, predecessor: PredAbsABEState) -> List[PredAbsABEState]:
        raise NotImplementedError

    def get_abstract_successors_for_edge(self,
                                         predecessor: PredAbsABEState,
                                         edge: CFAEdge
                                        ) -> List[PredAbsABEState]:
        # 1) Copy SSA indices locally
        ssa_idx = copy.deepcopy(predecessor.ssa_indices)

        is_block_head = self.is_block_head(edge.predecessor)


        kind = edge.instruction.kind
        if   kind == InstructionType.STATEMENT:
            trans = PredAbsPrecision.ssa_from_assign(edge, ssa_indices=ssa_idx)
        elif kind == InstructionType.ASSUMPTION:
            expr = PredAbsPrecision.ssa_from_assume(edge, ssa_indices=ssa_idx)

            predecessor_formula = PredAbsPrecision.ssa_set_indices(And(predecessor.predicates), predecessor.ssa_indices)
            if not is_sat(And(expr, predecessor_formula)):
                return []

            trans = expr
        elif kind == InstructionType.CALL:
            trans = PredAbsPrecision.ssa_from_call(edge, ssa_indices=ssa_idx)
        elif kind == InstructionType.REACH_ERROR:
            # **special case**: hitting an error-edge → FALSE
            trans = FALSE()
        else:
            trans = TRUE()

        # compute successor formulas
        path_formula = And(predecessor.path_formula, trans)
        predicates   = predecessor.predicates

        if is_block_head:
            # 3) If this is truly unsatisfiable (i.e. error-edge), preserve it
            if trans.is_false():
                succ = PredAbsABEState()
                succ.ssa_indices = ssa_idx
                succ.predicates  = {trans}
                return [succ]

            # 4) Otherwise do Cartesian abstraction
            predicates = self._implied_predicates(
                predecessor.predicates,
                trans,
                self.precision[edge.successor]
            )

            path_formula = TRUE()

        succ = PredAbsABEState()
        succ.ssa_indices = ssa_idx
        succ.predicates  = predicates
        succ.path_formula = path_formula
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


