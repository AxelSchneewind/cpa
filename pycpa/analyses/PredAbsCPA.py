#!/usr/bin/env python
"""
Predicate-abstraction CPA with Cartesian abstraction and SSA support.
Replace the old file with this one.

Depends on:
    pysmt   (for SMT and interpolation)
    pycpa.* (your project modules)
"""

from __future__ import annotations
import sys
import copy
from typing import List, Set, Dict

from pysmt.shortcuts import And, Not, TRUE, is_sat
import pysmt.fnode as fnode

from pycpa.cfa import InstructionType, CFAEdge          # type: ignore
from pycpa.cpa import (CPA, AbstractState, TransferRelation,
                       StopSepOperator, MergeSepOperator)

from pycpa.analyses.PredAbsPrecision import PredAbsPrecision
from pysmt.exceptions import SolverReturnedUnknownResultError

try:
    from pycpa.cfa import InstructionType, CFAEdge
except ImportError:
    from cfa import InstructionType, CFAEdge



# --------------------------------------------------------------------------- #
# Abstract State
# --------------------------------------------------------------------------- #
class PredAbsState(AbstractState):
    """
    ⟦state⟧  = set  P  of predicates known to hold, plus the current SSA indices.
    The lattice order is reverse set-inclusion on P (smaller set = stronger fact).
    """
    def __init__(self, other: 'PredAbsState' | None = None) -> None:
        if other is not None:
            self.predicates: Set[fnode.FNode] = set(other.predicates)
            self.ssa_indices: Dict[str, int] = copy.deepcopy(other.ssa_indices)
        else:
            self.predicates = set()
            self.ssa_indices = {}

    # --- lattice helpers --------------------------------------------------- #
    def subsumes(self, other: 'PredAbsState') -> bool:
        """`self` subsumes `other`  ⇔  self.predicates ⊇ other.predicates."""
        return other.predicates.issubset(self.predicates)

    # --- python housekeeping ---------------------------------------------- #
    def __eq__(self, other: object) -> bool:          # type: ignore[override]
        if not isinstance(other, PredAbsState):
            return False
        return (self.predicates == other.predicates
                and self.ssa_indices == other.ssa_indices)

    def __hash__(self) -> int:
        return (hash(frozenset(self.predicates))
                ^ hash(frozenset(self.ssa_indices.items())))

    def __str__(self) -> str:
        preds = ', '.join(str(p) for p in self.predicates)
        return '{' + preds + '}'


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

    # -- helper ------------------------------------------------------------- #
    @staticmethod
    def _implied_predicates(ctx: Set[fnode.FNode], trans: fnode.FNode, precision: Set[fnode.FNode]) -> Set[fnode.FNode]:
        """
        Return { p ∈ precision |  ctx ∧ trans ⇒ p }.
        """
        phi = And(list(ctx)) if ctx else TRUE()
        phi = And(phi, trans)

        implied: Set[fnode.FNode] = set()
        for p in precision:
            try:
                sat = is_sat(And(phi, Not(p)))   # check if φ ∧ ¬p is SAT
            except SolverReturnedUnknownResultError:
                sat = True                      # “unknown” → assume SAT

            if not sat:                         # UNSAT ⇒ implication holds
                implied.add(p)

        # --- verbose logging (after implied is complete) -----------------
        import sys
        _seen_sets: set[frozenset] = set()      # module-level cache

        # … after you have built `implied` …

        main = sys.modules.get("__main__")
        if getattr(main, "args", None) and main.args.verbose:
            key = frozenset(implied)
            if key not in getattr(PredAbsCPA, "_seen_predsets", set()):
                PredAbsCPA._seen_predsets = getattr(PredAbsCPA, "_seen_predsets", set())
                PredAbsCPA._seen_predsets.add(key)
                print("  new predicate set:", '{' + ', '.join(map(str, implied)) + '}')
        return implied

    # -- interface ---------------------------------------------------------- #
    def get_abstract_successors(self, predecessor: PredAbsState
                                ) -> List[PredAbsState]:
        raise NotImplementedError

    def get_abstract_successors_for_edge(self,
                                         predecessor: PredAbsState,
                                         edge: CFAEdge) -> List[PredAbsState]:
        # --- compute concrete SP in SSA form ------------------------------ #
        # Make a *copy* of SSA indices so we don’t mutate the predecessor.
        ssa_idx = copy.deepcopy(predecessor.ssa_indices)

        match edge.instruction.kind:
            case InstructionType.STATEMENT:
                trans = PredAbsPrecision.ssa_from_assign(edge, ssa_indices=ssa_idx)
            case InstructionType.ASSUMPTION:
                trans = PredAbsPrecision.ssa_from_assume(edge, ssa_indices=ssa_idx)
            case _:
                # Calls, nondet, etc. – over-approximate with TRUE.
                trans = TRUE()

        if trans is None:
            trans = TRUE()

        # --- Cartesian abstraction --------------------------------------- #
        new_preds = self._implied_predicates(predecessor.predicates,
                                             trans,
                                             self.precision)

        succ = PredAbsState()
        succ.predicates = new_preds
        succ.ssa_indices = ssa_idx
        return [succ]


# --------------------------------------------------------------------------- #
# CPA wrapper
# --------------------------------------------------------------------------- #
class PredAbsCPA(CPA):
    """
    A single-component CPA (can later be composed with LocationCPA, etc.).
    """
    def __init__(self, initial_precision) -> None:
        # accept PredAbsPrecision *or* raw set
        self.precision = (initial_precision.predicates
                          if hasattr(initial_precision, "predicates")
                          else set(initial_precision))

    # -- CPA interface ------------------------------------------------------ #
    def get_initial_state(self) -> PredAbsState:
        return PredAbsState()

    def get_stop_operator(self) -> StopSepOperator:
        return StopSepOperator(PredAbsState.subsumes)

    def get_merge_operator(self) -> MergeSepOperator:
        return MergeSepOperator()        # merge-sep (no joining)

    def get_transfer_relation(self) -> TransferRelation:
        return PredAbsTransferRelation(self.precision)
