#!/usr/bin/env python
"""
Configuration for Predicate Analysis.

This configuration sets up a CPA stack using:
- StackCPA for handling function calls and returns.
- CompositeCPA to combine:
    - LocationCPA for tracking CFA node locations.
    - PredAbsCPA for predicate abstraction using the computed precision.
"""

import pprint
from typing import List, Any, Dict

# CPAs used in this configuration
from pycpa.analyses import PredAbsCPA, LocationCPA, StackCPA, CompositeCPA
# Precision object specific to Predicate Abstraction
from pycpa.analyses.PredAbsPrecision import PredAbsPrecision

# Assuming CFANode is defined here for type hinting, adjust if it's elsewhere
from pycpa.cfa import CFANode

def get_cpas(entry_point: CFANode, 
             cfa_roots: List[CFANode], 
             output_dir: str, 
             **params: Dict[str, Any]) -> List[StackCPA]:
    """
    Configures and returns the list of CPAs for Predicate Analysis.
    """
    print(f"\n[Config PredicateAnalysis INFO] Setting up PredicateAnalysis CPA stack.")
    assert entry_point is not None, "Entry point CFANode must be provided."

    if not cfa_roots: # Ensure cfa_roots is not empty
        print("[Config PredicateAnalysis WARN] cfa_roots is empty, using entry_point as the only root.")
        cfa_roots = [entry_point]
    
    # 1. Initialize Predicate Precision
    print(f"[Config PredicateAnalysis INFO] Generating initial predicate precision from {len(cfa_roots)} CFA root(s)...")
    precision = PredAbsPrecision.from_cfa(cfa_roots)
    print(f"[Config PredicateAnalysis INFO] Initial precision created: {precision}")

    # 2. Dump initial precision to a file if output_dir is provided
    if output_dir:
        precision_file_path = output_dir + '/precision_initial.txt'
        print(f"[Config PredicateAnalysis INFO] Dumping initial global predicates to: {precision_file_path}")
        try:
            with open(precision_file_path, 'w') as f:
                f.write("Initial Global Predicates:\n")
                f.write(pprint.pformat(precision.global_predicates))
            print(f"[Config PredicateAnalysis INFO] Successfully dumped initial predicates.")
        except Exception as e:
            print(f"[Config PredicateAnalysis ERROR] Failed to dump precision: {e}")

    # 3. Construct the CPA stack
    print("[Config PredicateAnalysis INFO] Building CPA instances...")
    pred_abs_cpa = PredAbsCPA(initial_precision=precision)
    print(f"[Config PredicateAnalysis DEBUG]   PredAbsCPA instance created with precision: {precision}")
    
    location_cpa = LocationCPA(cfa_root=entry_point)
    print(f"[Config PredicateAnalysis DEBUG]   LocationCPA instance created with root: {entry_point.node_id if entry_point else 'None'}")
    
    # MODIFIED HERE: Pass the list as a positional argument
    abstraction_cpas = CompositeCPA([location_cpa, pred_abs_cpa])
    print(f"[Config PredicateAnalysis DEBUG]   CompositeCPA (for abstraction) instance created.")

    final_cpa_component = StackCPA(wrapped_cpa=abstraction_cpas)
    print(f"[Config PredicateAnalysis DEBUG]   StackCPA instance created, wrapping abstraction CompositeCPA.")
    
    print(f"[Config PredicateAnalysis INFO] PredicateAnalysis CPA stack configuration complete.")
    return [final_cpa_component]

