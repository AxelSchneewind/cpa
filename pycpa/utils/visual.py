#!/usr/bin/env python3
"""
pycpa.utils.visual
------------------

Reusable helpers for drawing ASTs, CFAs, ARGs … with Graphviz.

• Graphable           – minimal interface a node must implement
• graphable_to_dot()  – generic breadth-first walk → graphviz.Digraph
• ASTVisualizer       – ast.NodeVisitor ⇒ Graphviz graph of the AST
"""

from __future__ import annotations
import ast
from typing import Iterable
from graphviz import Digraph


# ------------------------------------------------------------------ #
#  very small “interface”                                            #
# ------------------------------------------------------------------ #
class Graphable:
    def get_node_label(self) -> str: ...
    def get_successors (self) -> Iterable["Graphable"]: ...
    def get_edge_labels(self, succ: "Graphable") -> Iterable[str]: ...


# ------------------------------------------------------------------ #
#  generic Graphable → graphviz helper                               #
# ------------------------------------------------------------------ #
def graphable_to_dot(roots: Iterable[Graphable],
                     *,
                     name: str = "G") -> Digraph:
    g = Digraph(name=name, graph_attr={"rankdir": "LR"})
    seen: set[Graphable] = set()

    def visit(n: Graphable):
        if n in seen:
            return
        seen.add(n)
        g.node(str(id(n)), label=n.get_node_label(), shape="box")
        for succ in n.get_successors():
            visit(succ)
            for lbl in n.get_edge_labels(succ):
                g.edge(str(id(n)), str(id(succ)), label=lbl)

    for r in roots:
        visit(r)
    return g


# ------------------------------------------------------------------ #
#  AST → Graphviz                                                    #
# ------------------------------------------------------------------ #
class ASTVisualizer(ast.NodeVisitor):
    """
    Usage:
        v = ASTVisualizer()
        v.visit(ast_tree)
        v.graph.render("out/ast")
    """
    def __init__(self):
        self.graph = Digraph("AST", node_attr={"shape": "box"})
        self._idx  = 0
        self._stack: list[str] = []

    # helpers --------------------------------------------------------
    def _new_id(self) -> str:
        self._idx += 1
        return f"n{self._idx}"

    def _add_node(self, label: str) -> str:
        nid = self._new_id()
        self.graph.node(nid, label=label)
        if self._stack:
            self.graph.edge(self._stack[-1], nid)
        return nid

    # generic visitors ----------------------------------------------
    def generic_visit(self, node):
        label = type(node).__name__
        if isinstance(node, ast.Constant):
            label += f"\\n{repr(node.value)}"
        elif isinstance(node, ast.Name):
            label += f"\\n{node.id}"
        cur = self._add_node(label)
        self._stack.append(cur)
        super().generic_visit(node)
        self._stack.pop()

