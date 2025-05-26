#!/usr/bin/env python
"""CEGAR helper utilities

Two high-level helpers used by the refinement loop
-------------------------------------------------
* is_path_feasible(path_edges)             → bool
* refine_precision(path_edges, old_prec)   → set(FNode)

They build formulas **in SSA form** so variables from different edges
cannot clash, and they use pysmt for SAT + interpolation.
"""

from __future__ import annotations
from typing import List, Set, Dict

from pysmt.shortcuts import And, is_sat, TRUE
from pysmt.solvers.interpolation import Interpolator
from pysmt.fnode import FNode

# — robust imports whether code lives in a flat folder or a package —
try:
    from pycpa.cfa import InstructionType, CFAEdge          # type: ignore
except ImportError:
    from cfa import InstructionType, CFAEdge                # type: ignore

try:
    from pycpa.analyses.PredAbsPrecision import PredAbsPrecision
except ImportError:
    from PredAbsPrecision import PredAbsPrecision


# --------------------------------------------------------------------------- #
# Internal: translate one CFA edge into an SSA formula
# --------------------------------------------------------------------------- #
def _edge_formula_ssa(edge: CFAEdge, ssa_idx: Dict[str, int]) -> FNode:
    """Return a Boolean pysmt formula for *edge* and update `ssa_idx`."""
    match edge.instruction.kind:
        case InstructionType.STATEMENT:
            return PredAbsPrecision.ssa_from_assign(edge, ssa_idx)
        case InstructionType.ASSUMPTION:
            return PredAbsPrecision.ssa_from_assume(edge, ssa_idx)
        case _:
            # calls, nondet, etc. – sound over-approximation
            return TRUE()


# --------------------------------------------------------------------------- #
# 1.  Feasibility check
# --------------------------------------------------------------------------- #
def is_path_feasible(path_edges: List[CFAEdge]) -> bool:
    """Concrete feasibility check for an abstract counter-example path."""
    ssa_idx: Dict[str, int] = {}
    phi = TRUE()
    for e in path_edges:
        phi = And(phi, _edge_formula_ssa(e, ssa_idx))
    return is_sat(phi)


# --------------------------------------------------------------------------- #
# 2.  Precision refinement via interpolation
# --------------------------------------------------------------------------- #
def refine_precision(path_edges: List[CFAEdge],
                     old_precision: Set[FNode]) -> Set[FNode]:
    """
    Given a *spurious* path, return an enlarged predicate set.
    """
    if not path_edges:
        return set(old_precision)

    assert isinstance(path_edges, list)
    assert len(path_edges) == 0 or isinstance(path_edges[0], CFAEdge)

    # Build per-edge SSA formulas  A₁,…,Aₙ
    formulas: List[FNode] = []
    ssa_idx: Dict[str, int] = {}
    for e in path_edges:
        formulas.append(_edge_formula_ssa(e, ssa_idx))

    # Need ≥2 blocks for sequence interpolation
    if len(formulas) == 1:
        formulas.append(TRUE())

    interp = Interpolator()
    try:
        itps = interp.sequence_interpolant(formulas)
    except Exception as exc:
        # Solver without interpolation support; keep old precision.
        print("[WARN] interpolation failed:", exc)
        return set(old_precision)

    new_preds: Set[FNode] = set(old_precision)
    for I in itps:
        for atom in I.get_atoms():
            if atom.get_type().is_bool_type():
                new_preds.add(atom)

    return new_preds
