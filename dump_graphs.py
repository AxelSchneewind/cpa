#!/usr/bin/env python3
# dump_graphs.py

from __future__ import annotations
import ast, sys, time, textwrap
from pathlib import Path
import astpretty
from graphviz import Digraph

from pycpa.preprocessor              import preprocess_ast
from pycpa.cfa                       import CFACreator
from pycpa.utils.visual              import ASTVisualizer, graphable_to_dot, Graphable
from pycpa.analyses.PredAbsCEGAR     import run_cegar, _analyse_once
from pycpa.analyses.PredAbsPrecision import PredAbsPrecision
from pycpa.analyses.ARGCPA           import ARGState
from pycpa.task                      import Task


def _write(path: Path, data: str | bytes) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(data, 'utf8') if isinstance(data, str) else path.write_bytes(data)


class GraphableCFANode(Graphable):
    def __init__(self, node): self.node = node
    def get_node_label(self): return str(self.node.node_id)
    def get_successors(self): return [GraphableCFANode(e.successor) for e in self.node.leaving_edges]
    def get_edge_labels(self, succ): return [e.label() for e in self.node.leaving_edges if e.successor == succ.node] or ['']
    def __eq__(self, other): return self.node == other.node
    def __hash__(self): return hash(self.node)


class GraphableARGState(Graphable):
    def __init__(self, st: ARGState): self.st = st
    def get_node_label(self): return str(self.st)
    def get_successors(self): return [GraphableARGState(ch) for ch in self.st.children]
    def get_edge_labels(self, succ): return ['']
    def __eq__(self, o): return self.st == o.st
    def __hash__(self): return hash(self.st)


def main(src: str) -> None:
    src_path = Path(src).resolve()
    if not src_path.exists(): sys.exit(f"{src_path} not found")

    out_dir = Path("out") / src_path.stem
    out_dir.mkdir(parents=True, exist_ok=True)

    code = src_path.read_text('utf8');            _write(out_dir / "program.py", code)
    tree = preprocess_ast(ast.parse(code, filename=str(src_path)))
    _write(out_dir / "program-preprocessed.py", ast.unparse(tree))
    _write(out_dir / "astpretty", astpretty.pformat(tree, show_offsets=False))

    vis = ASTVisualizer(); vis.visit(tree); vis.graph.render(out_dir / "ast", cleanup=True)

    cfa = CFACreator(); cfa.visit(tree)
    graphable_to_dot([GraphableCFANode(r) for r in cfa.roots]).render(out_dir / "cfa", cleanup=True)

    entry        = cfa.roots[0]            # first root = CFA entry node
    spec         = []                      # no spec objects required here
    task = Task(src_path.stem, max_iterations=100_000)


    t0 = time.time()
    verdict = run_cegar(entry, cfa.roots, task, spec, max_refinements=12, arg_node_cap=50_000, verbose=False)
    runtime = time.time() - t0

    π = PredAbsPrecision.from_cfa(cfa.roots).predicates
    _, algo = _analyse_once(entry, π, task, [], arg_cap=1_000_000)
    graphable_to_dot([GraphableARGState(algo.cpa.arg_root)]).render(out_dir / "arg", cleanup=True)

    summary = textwrap.dedent(f"""
        Source file : {src_path}
        Verdict     : {verdict}
        ARG nodes   : {len(algo.cpa._arg_nodes)}
        Runtime     : {runtime:.3f}s
    """).strip()
    _write(out_dir / "summary.txt", summary)
    print(summary); print(f"results in {out_dir}/")


if __name__ == "__main__":
    if len(sys.argv) != 2: sys.exit("usage: dump_graphs.py <python-source>")
    main(sys.argv[1])
