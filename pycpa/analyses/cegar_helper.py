#!/usr/bin/env python3
"""
CEGAR Helper for Boolean Predicate Abstraction.

Provides functions for:
1. Checking feasibility of an abstract counterexample path using an SMT solver.
2. Refining predicate precision using interpolants from a spurious counterexample.
"""

import pprint

from typing import List, Tuple, Optional, Dict, Set

from pysmt.fnode import FNode
from pysmt.shortcuts import Solver, And, Not, TRUE, FALSE, Interpolator

from pycpa.cfa import CFAEdge, CFANode, InstructionType
from pycpa.analyses.PredAbsPrecision import PredAbsPrecision
from pycpa.analyses.ssa_helper import SSA

from pycpa import log

import copy

def is_path_feasible(abstract_cex_edges: list[CFAEdge]) -> tuple[bool, list[FNode]]:
    """
    Checks if the abstract counterexample path is feasible.

    Args:
        abstract_cex_edges: A list of CFAEdges representing the abstract counterexample.

    Returns:
        A tuple:
        - bool: True if the path is feasible, False otherwise.
        - list[FNode]: A list of SMT formula conjuncts (A_1, ..., A_n) representing the path
    """
    log.printer.log_debug(5, "\n[CEGAR Helper INFO] Checking path feasibility...")
    assert abstract_cex_edges is not None

    path_formula_conjuncts: list[FNode] = []
    current_ssa_indices: dict[str, int] = {}

    for i, edge in enumerate(abstract_cex_edges):
        edge_formula = PredAbsPrecision.from_cfa_edge(edge, current_ssa_indices) if edge else TRUE()
        assert edge_formula       

        path_formula_conjuncts.append(edge_formula)

    full_path_formula = And(path_formula_conjuncts)

    log.printer.log_debug(1, f"[CEGAR Helper DEBUG] Full path formula (Φ) for feasibility check: {full_path_formula.serialize()}")

    with Solver(name="msat", logic="QF_BV") as solver:
        solver.add_assertion(full_path_formula)
        is_sat_result = solver.solve()
        log.printer.log_debug(1, f"[CEGAR Helper INFO] Path formula SMT check result: {'SAT' if is_sat_result else 'UNSAT'}")

        if is_sat_result:
            # Path is feasible (concrete counterexample)
            # TODO: Optionally extract model using solver.get_model() if needed for concrete trace
            return True, path_formula_conjuncts, solver.get_model()
        else:
            # Path is spurious
            return False, path_formula_conjuncts, None


def refine_precision(
    current_precision: PredAbsPrecision,
    abstract_cex_edges: List[CFAEdge],
    path_formula_conjuncts: List[FNode]
) -> PredAbsPrecision:
    """
    Refines the predicate precision using interpolants from a spurious counterexample.

    Args:
        current_precision: The PredAbsPrecision object to update.
        abstract_cex_edges: The list of CFAEdges of the spurious path.
        path_formula_conjuncts: The SMT formulas (A_1, ..., A_n) for the path,
                                whose conjunction is UNSAT.

    Returns:
        The updated PredAbsPrecision object.
    """
    log.printer.log_debug(1, "\n[CEGAR Helper INFO] Refining precision using interpolants...")
    if not path_formula_conjuncts:
        log.printer.log_debug(1, "[CEGAR Helper WARN] No path formula conjuncts provided for interpolation. Precision not refined.")
        return None

    # Use MathSAT (msat) for interpolation.
    interpolants: list[FNode]
    with Interpolator(name="msat", logic="QF_BV") as interpolator:
        # sequence_interpolant expects a list of formulas [A_1, ..., A_n]
        # whose conjunction is UNSAT. It returns a list of interpolants
        # [I_0, ..., I_{n-1}] where I_k is an interpolant for
        # (A_0 ^ ... ^ A_k) and (A_{k+1} ^ ... ^ A_{n-1}).
        # Note: pySMT's sequence_interpolant might return n-1 interpolants for n formulas.
        # The BPAC algorithm often refers to τ_0, ..., τ_n.
        # τ_0 = True, τ_n = False. τ_i is interpolant for (A_1...A_i) and (A_{i+1}...A_n)
        # Let's assume interpolator.sequence_interpolant([A1..An]) returns [Itp1, ..., Itp_{n-1}]
        # where Itp_k is for (A1..Ak) and (A_{k+1}..An)
        # We need to align this with the locations.
        log.printer.log_debug(1, f"[CEGAR Helper DEBUG] Requesting sequence interpolants for {len(path_formula_conjuncts)} conjuncts.")
        raw_interpolants = interpolator.sequence_interpolant(path_formula_conjuncts)
        assert raw_interpolants is not None

        # Construct the sequence τ_0, ..., τ_n as per typical CEGAR algorithm
        # τ_0 = True
        # τ_i for i=1..n-1 is raw_interpolants[i-1]
        # τ_n = False
        interpolants = [TRUE()] + raw_interpolants + [FALSE()]
        log.printer.log_debug(1, f"[CEGAR Helper INFO] Generated {len(interpolants)} interpolants (τ_0 to τ_n).")
        for i, itp in enumerate(interpolants):
            log.printer.log_debug(1, f"[CEGAR Helper DEBUG]   τ_{i}: {itp.serialize()}")

    new_local_predicates_map: Dict[CFANode, Set[FNode]] = {}

    # add predicates from τ_i (1 <= i <= n-1) to π(l_i) where l_i is abstract_cex_edges[i-1].successor
    num_edges = len(abstract_cex_edges)
    assert len(interpolants) == num_edges + 1
    for i in range(1, num_edges): # Corresponds to τ_1 to τ_{n-1} (or τ_m-1 if n=m)
        interp_formula = interpolants[i]
        if interp_formula.is_true() or interp_formula.is_false():
            continue

        # for assumptions, use predecessor (as predicate will be relevant for reachability)
        # for other edges, use successor   (as predicate might hold after this edge)
        location_node = abstract_cex_edges[i-1].predecessor if abstract_cex_edges[i-1].instruction.kind == InstructionType.ASSUMPTION else abstract_cex_edges[i-1].successor
        
        if location_node not in new_local_predicates_map:
            new_local_predicates_map[location_node] = set()
        
        for atom in interp_formula.get_atoms():
            if not atom.is_true() and not atom.is_false(): # Don't add True/False as predicates
                unindexed = SSA.unindex_predicate(atom)
                if location_node not in current_precision.predicates or unindexed not in current_precision.predicates[location_node]:
                    new_local_predicates_map[location_node].add(unindexed)
                    new_local_predicates_map[location_node].add(Not(unindexed))

    if len(new_local_predicates_map) > 0:      # only return new precision if new atoms found
        log.printer.log_debug(1, f"[CEGAR Helper INFO] Adding new local predicates to precision: { {loc.node_id: preds for loc, preds in new_local_predicates_map.items()} }")
        new_precision = copy.copy(current_precision)
        new_precision.add_local_predicates(new_local_predicates_map)
        return new_precision, interpolants
    else:                           # return old precision
        log.printer.log_debug(1, "[CEGAR Helper INFO] No new non-trivial predicates extracted from interpolants.")
        return current_precision, None


