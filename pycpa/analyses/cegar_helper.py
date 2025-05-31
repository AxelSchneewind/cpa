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
from pysmt.exceptions import SolverReturnedUnknownResultError, NoSolverAvailableError

# Assuming PredAbsPrecision and CFANode/CFAEdge are in these locations
# Adjust imports based on your project structure
from pycpa.cfa import CFAEdge, CFANode
from pycpa.analyses.PredAbsPrecision import PredAbsPrecision, unindex_predicate

from pycpa import log

def is_path_feasible(abstract_cex_edges: List[CFAEdge]) -> Tuple[bool, Optional[List[FNode]]]:
    """
    Checks if the abstract counterexample path is feasible.

    Args:
        abstract_cex_edges: A list of CFAEdges representing the abstract counterexample.

    Returns:
        A tuple:
        - bool: True if the path is feasible, False otherwise.
        - Optional[List[FNode]]: A list of SMT formula conjuncts (A_1, ..., A_n)
                                 representing the path if it's UNSAT (spurious).
                                 None if the path is SAT (feasible) or on error.
    """
    log.printer.log_debug(5, "\n[CEGAR Helper INFO] Checking path feasibility...")
    if not abstract_cex_edges:
        log.printer.log_debug(3, "[CEGAR Helper WARN] Path is empty, considering it trivially feasible (or an issue).")
        return True, None # Or handle as an error/spurious based on semantics

    path_formula_conjuncts: List[FNode] = []
    # For feasibility check, we start with a fresh SSA map for this specific path
    # This is independent of the SSA maps used during ARG construction for abstraction states
    current_ssa_indices: Dict[str, int] = {}

    log.printer.log_debug(7, f"[CEGAR Helper DEBUG] Abstract CEX Path Edges ({len(abstract_cex_edges)}):")
    for i, edge in enumerate(abstract_cex_edges):
        log.printer.log_debug(1, f"[CEGAR Helper DEBUG]   Edge {i}: {edge.label()} (from {edge.predecessor.node_id} to {edge.successor.node_id})")
        
        # PredAbsPrecision.from_cfa_edge generates the SMT formula for the edge
        # and updates current_ssa_indices internally.
        edge_formula = PredAbsPrecision.from_cfa_edge(edge, current_ssa_indices)
        
        if edge_formula is None:
            log.printer.log_debug(0, f"[CEGAR Helper WARN] Could not get SMT formula for edge: {edge.label()}. Skipping.")
            # Or treat as TRUE, or error, depending on desired strictness
            edge_formula = TRUE() # Default to TRUE if no formula, to not break path conjunction

        log.printer.log_debug(3, f"[CEGAR Helper DEBUG]     Edge SMT: {edge_formula.serialize() if edge_formula else 'None'}")
        log.printer.log_debug(3, f"[CEGAR Helper DEBUG]     SSA after edge: {current_ssa_indices}")

        path_formula_conjuncts.append(edge_formula)


    assert path_formula_conjuncts is not None
    full_path_formula = And(path_formula_conjuncts)
    assert full_path_formula is not None

    log.printer.log_debug(1, f"[CEGAR Helper DEBUG] Full path formula (Φ) for feasibility check: {full_path_formula.serialize()}")

    # Using MathSAT (msat) as the solver, ensure it's installed and pySMT can find it.
    # QF_LIA is a common logic for integer programs. Adjust if your program uses reals, etc.
    with Solver(name="msat", logic="QF_LIA") as solver:
        solver.add_assertion(full_path_formula)
        is_sat_result = solver.solve()
        log.printer.log_debug(1, f"[CEGAR Helper INFO] Path formula SMT check result: {'SAT' if is_sat_result else 'UNSAT'}")

        if is_sat_result:
            # Path is feasible (concrete counterexample)
            # TODO: Optionally extract model using solver.get_model() if needed for concrete trace
            return True, None
        else:
            # Path is spurious
            return False, path_formula_conjuncts # Return the conjuncts for interpolation


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

    interpolants: Optional[List[FNode]] = None
    try:
        # Use MathSAT (msat) for interpolation.
        with Interpolator(name="msat", logic="QF_LIA") as interpolator:
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
            
            if raw_interpolants is None:
                log.printer.log_debug(1, "[CEGAR Helper WARN] Interpolator returned None. Cannot refine precision.")
                return None

            # Construct the sequence τ_0, ..., τ_n as per typical CEGAR algorithm
            # τ_0 = True
            # τ_i for i=1..n-1 is raw_interpolants[i-1]
            # τ_n = False
            interpolants = [TRUE()] + raw_interpolants + [FALSE()]
            log.printer.log_debug(1, f"[CEGAR Helper INFO] Generated {len(interpolants)} interpolants (τ_0 to τ_n).")
            for i, itp in enumerate(interpolants):
                log.printer.log_debug(1, f"[CEGAR Helper DEBUG]   τ_{i}: {itp.serialize()}")

    except NoSolverAvailableError:
        log.printer.log_debug(1, "[CEGAR Helper ERROR] MathSAT solver (for interpolation) not found.")
        return None
    except SolverReturnedUnknownResultError:
        log.printer.log_debug(1, "[CEGAR Helper WARN] Interpolator returned UNKNOWN.")
        return None
    except Exception as e:
        log.printer.log_debug(1, f"[CEGAR Helper ERROR] Error during interpolation: {e}")
        return None

    if not interpolants:
        return None

    # --- Extract atomic predicates from interpolants and update precision ---
    # The interpolant τ_i is associated with the state *before* edge A_{i+1}
    # (or at location l_i, which is the predecessor of edge i).
    # Predicates from τ_i are added to π(l_i).
    # abstract_cex_edges: [edge_0, edge_1, ..., edge_{m-1}] (m edges)
    # path_formula_conjuncts: [A_0, A_1, ..., A_{n-1}] (n conjuncts, usually n=m)
    # interpolants: [τ_0, τ_1, ..., τ_n] (n+1 interpolants)
    # τ_i is for the state between A_i and A_{i+1} (using 1-based A for clarity here)
    # So, τ_i is relevant for location l_i = predecessor of edge_i (or successor of edge_{i-1})

    new_local_predicates_map: Dict[CFANode, Set[FNode]] = {}

    # τ_0 is True, τ_n is False. We are interested in τ_1, ..., τ_{n-1} primarily.
    # However, predicates can be extracted from all τ_i (except True/False).
    # The location for τ_i (0 < i < n) is abstract_cex_edges[i-1].successor
    # which is also abstract_cex_edges[i].predecessor.
    # For τ_0, it's abstract_cex_edges[0].predecessor.
    # For τ_n, it's abstract_cex_edges[n-1].successor.

    num_edges = len(abstract_cex_edges)
    if len(interpolants) != num_edges + 1:
        log.printer.log_debug(1, f"[CEGAR Helper WARN] Mismatch in interpolant count ({len(interpolants)}) and edge count ({num_edges}). Cannot reliably map interpolants to locations.")
        # Fallback: add all new predicates globally if mapping is unclear
        all_new_preds_globally = set()
        for itp in interpolants:
            if not itp.is_true() and not itp.is_false():
                for atom in itp.get_atoms():
                    if not atom.is_true() and not atom.is_false():
                         all_new_preds_globally.add(unindex_predicate(atom))
        if all_new_preds_globally:
            log.printer.log_debug(1, f"[CEGAR Helper INFO] Adding {len(all_new_preds_globally)} new predicates globally due to interpolant mapping uncertainty.")
            current_precision.add_global_predicates(all_new_preds_globally)
        return current_precision


    # Add predicates from τ_0 to π(l_0) where l_0 is abstract_cex_edges[0].predecessor
    location_node = abstract_cex_edges[0].predecessor
    if not interpolants[0].is_true() and not interpolants[0].is_false():
        if location_node not in new_local_predicates_map:
            new_local_predicates_map[location_node] = set()
        for atom in interpolants[0].get_atoms():
            if not atom.is_true() and not atom.is_false():
                if location_node not in current_precision.local_predicates or unindexed not in current_precision.local_predicates[location_node]:
                    new_local_predicates_map[location_node].add(unindexed)
                    current_atoms.add(unindexed)
        log.printer.log_debug(1, f"[CEGAR Helper DEBUG] Extracted from τ_0 for loc {loc_for_tau0.node_id}: {new_local_predicates_map[loc_for_tau0]}")


    # Add predicates from τ_i (1 <= i <= n-1) to π(l_i) where l_i is abstract_cex_edges[i-1].successor
    for i in range(1, num_edges): # Corresponds to τ_1 to τ_{n-1} (or τ_m-1 if n=m)
        interp_formula = interpolants[i]
        if interp_formula.is_true() or interp_formula.is_false():
            continue

        # Location l_i is the state *after* edge_{i-1} / block A_i
        # This is abstract_cex_edges[i-1].successor
        # This is also abstract_cex_edges[i].predecessor
        location_node = abstract_cex_edges[i-1].successor 
        
        if location_node not in new_local_predicates_map:
            new_local_predicates_map[location_node] = set()
        
        current_atoms = set()
        for atom in interp_formula.get_atoms():
            if not atom.is_true() and not atom.is_false(): # Don't add True/False as predicates
                unindexed = unindex_predicate(atom)
                if location_node not in current_precision.local_predicates or unindexed not in current_precision.local_predicates[location_node]:
                    new_local_predicates_map[location_node].add(unindexed)
                    current_atoms.add(unindexed)
        if current_atoms:
            log.printer.log_debug(1, f"[CEGAR Helper DEBUG] Extracted from τ_{i} for loc {location_node.node_id}: {current_atoms}")


    # Add predicates from τ_n to π(l_n) where l_n is abstract_cex_edges[n-1].successor (error location)
    location_node = abstract_cex_edges[num_edges-1].successor
    if not interpolants[num_edges].is_true() and not interpolants[num_edges].is_false():
        if loc_for_taun not in new_local_predicates_map:
            new_local_predicates_map[location_node] = set()
        for atom in interpolants[num_edges].get_atoms():
            if not atom.is_true() and not atom.is_false():
                unindexed = unindex_predicate(atom)
                if location_node not in current_precision.local_predicates or unindexed not in current_precision.local_predicates[location_node]:
                    new_local_predicates_map[location_node].add(unindexed)
                    current_atoms.add(unindexed)
        log.printer.log_debug(1, f"[CEGAR Helper DEBUG] Extracted from τ_{num_edges} for loc {loc_for_taun.node_id}: {new_local_predicates_map[loc_for_taun]}")

    if len(current_atoms) > 0:      # only return new precision if new atoms found
        log.printer.log_debug(0, f"[CEGAR Helper INFO] Adding new local predicates to precision: { {loc.node_id: preds for loc, preds in new_local_predicates_map.items()} }")
        new_precision = copy.copy(current_precision)
        new_precision.add_local_predicates_map(new_local_predicates_map)
        return new_precision
    else:                           # return old precision
        log.printer.log_debug(0, "[CEGAR Helper INFO] No new non-trivial predicates extracted from interpolants.")
        return current_precision


