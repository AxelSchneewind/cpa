# #!/usr/bin/env python3
# """
# Predicate-Abstraction CEGAR driver for pycpa
# ===========================================

# This module builds  LocationCPA × PredAbsCPA, runs the standard
# work-list algorithm, and refines the global predicate precision π
# until it

#     • proves SAFE          → returns "TRUE"
#     • finds a real bug     → returns "FALSE"
#     • exhausts its budget  → returns "UNKNOWN"

# No other files need to change.
# """

# from __future__ import annotations
# from typing import List, Set, Tuple

# import sys
# from pysmt.fnode import FNode
# from pysmt.shortcuts import TRUE

# from pycpa.cfa import CFANode
# from pycpa.analyses.LocationCPA      import LocationCPA
# from pycpa.analyses.PredAbsCPA       import PredAbsCPA
# from pycpa.analyses.PredAbsPrecision import PredAbsPrecision
# from pycpa.analyses.CompositeCPA     import CompositeCPA
# from pycpa.analyses.ARGCPA           import ARGCPA
# from pycpa.cpaalgorithm              import CPAAlgorithm, Status

# from pycpa.refinement import cegar_helper  # is_path_feasible / refine_precision

# # --------------------------------------------------------------------------- #
# # INTERNAL – one run under a *fixed* precision                                #
# # --------------------------------------------------------------------------- #
# def _analyse(entry: CFANode,
#              precision: Set[FNode],
#              task, specs,
#              arg_cap: int
#             ) -> Tuple[Status, CPAAlgorithm]:
#     """
#     Run work-list algorithm once and return (Status, algo_instance).
#     If ARG exceeds arg_cap nodes → return Status.TIMEOUT.
#     """
#     cpa   = ARGCPA(CompositeCPA([LocationCPA(entry),
#                                  PredAbsCPA(precision)]))

#     init = cpa.get_initial_state()
#     reached, wl = {init}, {init}

#     algo = CPAAlgorithm(cpa, task, type("R", (), {})(), specs)
#     algo.run(reached, wl)          # ← only the two mandatory args

#     # manual budget check
#     if len(reached) >= arg_cap:
#         algo.result.status = Status.TIMEOUT

#     return algo.result.status, algo

# # --------------------------------------------------------------------------- #
# # PUBLIC – CEGAR loop                                                         #
# # --------------------------------------------------------------------------- #
# def run_cegar(entry: CFANode,
#               cfa_roots: List[CFANode],
#               task, specification,
#               *, max_refinements: int = 12,
#                  arg_node_cap:   int = 50_000,
#                  verbose: bool      = False) -> str:

#     π = PredAbsPrecision.from_cfa(cfa_roots).predicates

#     for k in range(max_refinements):
#         if verbose:
#             print(f"\n[CEGAR {k:02d}]  |π| = {len(π)}")

#         status, algo = _analyse(entry, π, task, specification, arg_node_cap)

#         # 0) proof succeeded
#         if status == Status.OK:
#             return "TRUE"
#         # 1) only TIMEOUT is treated as UNKNOWN
#         if status == Status.TIMEOUT:
#             return "UNKNOWN"
#         # (we deliberately do NOT bail out on Status.ERROR here,
#         #  so that we can extract the abstract counterexample)

#         # 2) extract abstract counterexample
#         # print("[DEBUG PredAbsCEGAR] retrieving abstract_cex_edges from CPAAlgorithm")
#         if not hasattr(algo, "abstract_cex_edges"):
#             raise AttributeError("run_cegar: CPAAlgorithm has no `abstract_cex_edges`")
#         cex_edges = algo.abstract_cex_edges
#         # print(f"[DEBUG PredAbsCEGAR] abstract cex path = {cex_edges}")

#         # 3) check feasibility
#         if cegar_helper.is_path_feasible(cex_edges):
#             return "FALSE"

#         # 4) not feasible → refine π and loop
#         π = cegar_helper.refine_precision(π, cex_edges)
#     # refinements exhausted
#     return "UNKNOWN"

# # PredAbsCEGAR.py

# from typing import List, Set
# from pycpa.cfa import CFANode
# from pycpa.analyses.PredAbsPrecision import PredAbsPrecision
# from pycpa.refinement import cegar_helper
# from pycpa.analyses.LocationCPA import LocationCPA
# from pycpa.analyses.PredAbsCPA     import PredAbsCPA
# from pycpa.analyses.CompositeCPA    import CompositeCPA
# from pycpa.analyses.ARGCPA          import ARGCPA
# from pycpa.cpaalgorithm             import CPAAlgorithm, Status

# def run_cegar(entry: CFANode,
#               cfa_roots: List[CFANode],
#               task, specification,
#               *, max_refinements: int = 12,
#                  arg_node_cap:   int = 50_000,
#                  verbose: bool      = False) -> str:

#     # 0) initialize precision π from all boolean atoms in the CFA
#     π = PredAbsPrecision.from_cfa(cfa_roots).predicates

#     # 1) perform up to max_refinements CEGAR iterations
#     for k in range(max_refinements):
#         if verbose:
#             print(f"\n[CEGAR {k:02d}]  |π| = {len(π)}")

#         # run one ARGCPA pass under the current π
#         status, algo = _analyse(entry, π, task, specification, arg_node_cap)

#         # 2) if SAFE, we’re done
#         if status == Status.OK:
#             return "TRUE"

#         # 3) if an abstract error was detected, bail out immediately
#         if status == Status.ERROR:
#             return "FALSE"

#         # 4) only TIMEOUT is treated as UNKNOWN
#         if status == Status.TIMEOUT:
#             return "UNKNOWN"

#         # 5) extract the abstract counterexample path
#         # print("[DEBUG PredAbsCEGAR] retrieving abstract_cex_edges from CPAAlgorithm")
#         if not hasattr(algo, "abstract_cex_edges"):
#             raise AttributeError("run_cegar: CPAAlgorithm lacks `abstract_cex_edges`")
#         cex_edges = algo.abstract_cex_edges
#         # print(f"[DEBUG PredAbsCEGAR] abstract cex path = {cex_edges}")

#         # 6) check concrete feasibility; if real bug, return FALSE
#         if cegar_helper.is_path_feasible(cex_edges):
#             return "FALSE"

#         # 7) spurious → refine precision π and continue
#         π = cegar_helper.refine_precision(π, cex_edges)

#     # refinement budget exhausted
#     return "UNKNOWN"


# #!/usr/bin/env python3
# """
# PredAbsCEGAR.py
# ===============

# Predicate-abstraction **C**ounter-**E**xample-**G**uided **A**bstraction
# **R**efinement driver for *pyCPA*.

# The module is self-contained: import it, call ``run_cegar`` with the CFA
# entry node, the list of CFA roots, the verification *task* object and the
# chosen *specification* CPA(s); it returns the usual verdict string
# ``"TRUE"``, ``"FALSE"`` or ``"UNKNOWN"``.

# Key design decisions
# --------------------
# * **ARGCPA** wraps a product of
#   ``LocationCPA × PredAbsCPA(π)`` – the precision π is refined across
#   iterations.
# * On every iteration we run the normal work-list algorithm
#   (``CPAAlgorithm``).  The algorithm records an *abstract* error path
#   (list of ``CFAEdge`` objects); the driver asks the SMT-based helper
#   ``cegar_helper.is_path_feasible`` whether the path is *concrete*.
# * Only a *concrete* error path terminates the loop with the verdict
#   ``"FALSE"`` – otherwise we refine π and try again.
# * The loop stops when:  
#   ─ the program is proven safe   → ``"TRUE"``  
#   ─ the refinement budget is used up or the ARG grows too large   → ``"UNKNOWN"``


# ------------------------------------------------------------------------
# """

# from __future__ import annotations

# from typing import List, Set, Tuple

# from pysmt.fnode import FNode
# from pysmt.shortcuts import TRUE  # convenience constant

# from pycpa.cfa                       import CFANode
# from pycpa.analyses.LocationCPA      import LocationCPA
# from pycpa.analyses.PredAbsCPA       import PredAbsCPA
# from pycpa.analyses.PredAbsPrecision import PredAbsPrecision
# from pycpa.analyses.CompositeCPA     import CompositeCPA
# from pycpa.analyses.ARGCPA           import ARGCPA
# from pycpa.cpaalgorithm              import CPAAlgorithm, Status

# # refinement helpers (SMT-based feasibility + predicate generation)
# from pycpa.refinement import cegar_helper


# # --------------------------------------------------------------------------- #
# # internal: run **one** analysis under a *fixed* predicate precision π        #
# # --------------------------------------------------------------------------- #
# def _analyse_once(entry        : CFANode,
#                   π            : Set[FNode],
#                   task,
#                   specs,
#                   arg_cap      : int
#                   ) -> Tuple[Status, CPAAlgorithm]:
#     """
#     Build LocationCPA × PredAbsCPA(π), execute the work-list algorithm,
#     return the resulting *status* and the *CPAAlgorithm* instance (for the
#     stored abstract counter-example, reached set size, …).

#     If the ARG grows beyond *arg_cap* nodes we treat it as a timeout so
#     the caller can translate that to the verdict “UNKNOWN”.
#     """
#     composite_cpa  = CompositeCPA([LocationCPA(entry), PredAbsCPA(π)])
#     cpa            = ARGCPA(composite_cpa)

#     init     = cpa.get_initial_state()
#     reached  = {init}
#     waitlist = {init}

#     algo = CPAAlgorithm(cpa, task, type("Res", (), {})(), specs)
#     algo.run(reached, waitlist)

#     if len(reached) >= arg_cap:
#         algo.result.status = Status.TIMEOUT

#     return algo.result.status, algo


# # --------------------------------------------------------------------------- #
# # public: full CEGAR loop                                                     #
# # --------------------------------------------------------------------------- #
# def run_cegar(entry              : CFANode,
#               cfa_roots          : List[CFANode],
#               task,
#               specification,
#               *,
#               max_refinements    : int  = 12,
#               arg_node_cap       : int  = 50_000,
#               verbose            : bool = False
#               ) -> str:
#     """
#     Execute the standard CEGAR loop.

#     Parameters
#     ----------
#     entry
#         CFA entry node of the *main* procedure.
#     cfa_roots
#         All CFA roots (one per Python function) – used to mine predicates.
#     task
#         The *Task* object created by the CLI front-end (iteration limits).
#     specification
#         List of specification CPA names (e.g. ``["ReachSafety"]``).
#     max_refinements, arg_node_cap, verbose
#         Tuning parameters; defaults suffice for the benchmark suite.

#     Returns
#     -------
#     str
#         ``"TRUE"``, ``"FALSE"`` or ``"UNKNOWN"`` (SV-COMP conventions).
#     """
#     # 0)  initial predicate precision  π₀  =  all Boolean atoms in the CFA
#     π = PredAbsPrecision.from_cfa(cfa_roots).predicates
#     if not π:
#         π = {TRUE()}            # guarantee π ≠ ∅ to placate SMT encodings

#     # --- main refinement loop ---------------------------------------------
#     for k in range(max_refinements):
#         if verbose:
#             print(f"\n[CEGAR {k:02d}]  |π| = {len(π)}")

#         status, algo = _analyse_once(entry, π, task,
#                                      specification, arg_node_cap)

#         # 1)  SUCCESS – proven safe
#         if status is Status.OK:
#             return "TRUE"

#         # 2)  gave up (ARG too large or user timeout)
#         if status is Status.TIMEOUT:
#             return "UNKNOWN"

#         # 3)  all other statuses should come with an abstract cex
#         cex_edges = getattr(algo, "abstract_cex_edges", None)
#         if not cex_edges:
#             # defensive: unexpected state => declare UNKNOWN
#             if verbose:
#                 print("[WARN]   no abstract counter-example returned")
#             return "UNKNOWN"

#         # optional pretty print
#         if verbose:
#             print("  abstract counter-example:",
#                   " ➔ ".join(f"{e.instruction}" for e in cex_edges))

#         # 4)  FEASIBILITY CHECK
#         if cegar_helper.is_path_feasible(cex_edges):
#             return "FALSE"      # real bug – stop!

#         # 5)  spurious – REFINE  π  and iterate
#         π = cegar_helper.refine_precision(π, cex_edges)

#     # 6)  refinement budget exhausted
#     return "UNKNOWN"

#!/usr/bin/env python3
# pycpa/analyses/PredAbsCEGAR.py
"""
CEGAR driver that returns **TRUE**, **FALSE** *or* **UNKNOWN**.

Works with the rest of your current repository (LocationCPA, PredAbsCPA,
ARGCPA, cegar_helper, …) and raises no import errors.
"""

from __future__ import annotations
from typing import List, Set, Tuple

from pysmt.fnode     import FNode
from pysmt.shortcuts import TRUE

from pycpa.cfa                       import CFANode
from pycpa.analyses.LocationCPA      import LocationCPA
from pycpa.analyses.PredAbsCPA       import PredAbsCPA
from pycpa.analyses.PredAbsPrecision import PredAbsPrecision
from pycpa.analyses.CompositeCPA     import CompositeCPA
from pycpa.analyses.ARGCPA           import ARGCPA
from pycpa.cpaalgorithm              import CPAAlgorithm, Status
from pycpa.refinement                import cegar_helper


# ──────────────────────────────────────────────────────────
# helper – run one analysis under a fixed predicate set π
# ──────────────────────────────────────────────────────────
def _analyse_once(entry: CFANode,
                  π: Set[FNode],
                  task,
                  specs,
                  arg_cap: int
                  ) -> Tuple[Status, CPAAlgorithm]:

    cpa      = ARGCPA(CompositeCPA([LocationCPA(entry), PredAbsCPA(π)]))
    init     = cpa.get_initial_state()
    reached  = {init}
    waitlist = {init}

    algo = CPAAlgorithm(cpa, task, type("Res", (), {})(), specs)
    algo.run(reached, waitlist)

    # oversize ARG → timeout ⇒ UNKNOWN
    if len(reached) >= arg_cap:
        algo.result.status = Status.TIMEOUT

    return algo.result.status, algo


# ──────────────────────────────────────────────────────────
# public – main CEGAR loop
# ──────────────────────────────────────────────────────────
def run_cegar(entry             : CFANode,
              cfa_roots         : List[CFANode],
              task,
              specification,
              *,
              max_refinements   : int  = 12,
              arg_node_cap      : int  = 50_000,
              verbose           : bool = False
              ) -> str:
    """
    Returns "TRUE", "FALSE", or "UNKNOWN" (SV-COMP convention).
    """

    # initial precision = Boolean atoms mined from the CFA
    π = PredAbsPrecision.from_cfa(cfa_roots).predicates or {TRUE()}

    for k in range(max_refinements):
        if verbose:
            print(f"[CEGAR {k:02d}]  |π| = {len(π)}")

        status, algo = _analyse_once(entry, π, task,
                                     specification, arg_node_cap)

        # safe program proven
        if status is Status.OK:
            return "TRUE"

        # resource limit hit
        if status is Status.TIMEOUT:
            return "UNKNOWN"

        # must have an abstract counter-example now
        cex_edges = getattr(algo, "abstract_cex_edges", None)
        if not cex_edges:
            return "UNKNOWN"                   # defensive fallback

        # feasibility check
        if cegar_helper.is_path_feasible(cex_edges):
            return "FALSE"                     # real bug

        # spurious → refine predicate set
        π = cegar_helper.refine_precision(π, cex_edges)

    # refinement budget exhausted
    return "UNKNOWN"
