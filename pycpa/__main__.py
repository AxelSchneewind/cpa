#!/usr/bin/env python3
"""
Unified launcher for pycpa
==========================

* If PredicateAnalysis is among -c configs  →  CEGAR loop
* Otherwise run the classical CPAAlgorithm once
"""

from __future__ import annotations
import sys, ast, pathlib
from typing import List

from pycpa.params  import parser
from pycpa import configs
from pycpa.preprocessor import preprocess_ast
from pycpa.cfa            import CFACreator, CFANode
from pycpa.task           import Task, Result
from pycpa.verdict        import Verdict
from pycpa.analyses       import CompositeCPA, ARGCPA
from pycpa.cpaalgorithm   import CPAAlgorithm, Status

# CEGAR driver (uses PredicateAnalysis helpers)
from pycpa.analyses.PredAbsCEGAR import run_cegar

# --------------------------------------------------------------------------- #
#  helper: run classical CPA stack once                                       #
# --------------------------------------------------------------------------- #
def _run_once(entry: CFANode,
              cfa_roots: List[CFANode],
              args):
    analysis_mods      = [configs.load_cpa(c)           for c in args.config]
    specification_mods = [configs.load_specification(p) for p in args.property]

    cpas = []
    for m in analysis_mods:
        cpas.extend(m.get_cpas(entry_point=entry,
                               cfa_roots=cfa_roots,
                               output_dir=None))
    for s in specification_mods:
        cpas.extend(s.get_cpas(entry_point=entry,
                               cfa_roots=cfa_roots,
                               output_dir=None))

    cpa   = ARGCPA(CompositeCPA(cpas))
    init  = cpa.get_initial_state()
    wl    = {init};  reached = {init}
    result = Result()
    algo  = CPAAlgorithm(cpa,
                         Task(args.program[0], args.config, args.property,
                              max_iterations=args.max_iterations),
                         result,
                         specification_mods)
    algo.run(reached, wl, args.max_iterations)

    print("Status:", result.status)
    for i, spec in enumerate(specification_mods):
        v = spec.check_arg_state(init)
        print(f"{args.property[i]}: {v}")

# --------------------------------------------------------------------------- #
#  analyse a single input file                                                #
# --------------------------------------------------------------------------- #
def analyse_one(program: str, args):
    name = pathlib.Path(program).stem
    print(f"\n[VERIFICATION] Verifying {name} using {args.config} against {args.property}")

    # 1. preprocess & parse
    src   = pathlib.Path(program).read_text()
    tree  = preprocess_ast(ast.parse(src))

    # 2. build CFA
    creator = CFACreator(); creator.visit(tree)
    entry   = creator.entry_point

    # 3. PredicateAnalysis present?  →  run CEGAR
    if "PredicateAnalysis" in args.config:
        verdict = run_cegar(
            entry           = entry,
            cfa_roots       = creator.roots,
            task            = Task(program, args.config, args.property,
                                   max_iterations=args.max_iterations),
            specification   = [configs.load_specification(p) for p in args.property],
            max_refinements = 12,
            arg_node_cap    = args.max_iterations,
            verbose         = args.verbose,
        )
        print("[VERIFICATION] Final verdict:", verdict)
    else:
        _run_once(entry, creator.roots, args)

# --------------------------------------------------------------------------- #
#  main                                                                       #
# --------------------------------------------------------------------------- #
if __name__ == "__main__":
    args = parser.parse_args()          # flags defined only in params.py
    sys.modules["__main__"].args = args # for verbose checks in other modules

    for prog in args.program:
        analyse_one(prog, args)
