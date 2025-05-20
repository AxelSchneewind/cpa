#!/usr/bin/env python3
"""
pycpa.utils.visual
------------------

Reusable helpers for drawing ASTs, CFAs, ARGs … with Graphviz.

• Graphable           – minimal interface a node must implement
• cfa_to_dot()  – generic breadth-first walk → graphviz.Digraph
• arg_to_dot()  – generic breadth-first walk → graphviz.Digraph
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
def cfa_to_dot(roots, nodeattrs={"shape": "circle"}):
    assert isinstance(roots, list)
    dot = Digraph()
    for (key, value) in nodeattrs.items():
        dot.attr("node", [(key, value)])
    for root in roots:
        dot.node(str(root.get_node_id()), label=root.get_node_label())
        waitlist = set()
        waitlist.add(root)
        reached = set()
        reached.add(root)
        while not len(waitlist) == 0:
            node = waitlist.pop()
            dot.node(str(node.get_node_id()), label=node.get_node_label())
            reached.add(node)
            for successor in node.get_successors():
                for edgelabel in node.get_edge_labels(successor):
                    dot.edge(str(node.get_node_id()), str(successor.get_node_id()), label=edgelabel)
                if successor not in reached:
                    waitlist.add(successor)
    return dot

def arg_to_dot(roots, nodeattrs={"shape": "circle"}):
    assert isinstance(roots, list)
    dot = Digraph()
    for (key, value) in nodeattrs.items():
        dot.attr("node", [(key, value)])
    for root in roots:
        dot.node(str(root.get_node_id()), label=root.get_node_label())
        waitlist = set()
        waitlist.add(root)
        reached = set()
        reached.add(root)
        while not len(waitlist) == 0:
            node = waitlist.pop()

            label = node.get_node_label()
            assert label is not None and len(label) > 0
            if 'unsafe' in label:
                dot.node(str(node.get_node_id()), label=label, color='red')
            else:
                dot.node(str(node.get_node_id()), label=label)
            reached.add(node)

            for successor in node.get_successors():
                for edgelabel in node.get_edge_labels(successor):
                    dot.edge(str(node.get_node_id()), str(successor.get_node_id()), label=edgelabel)
                if successor not in reached:
                    waitlist.add(successor)
    return dot


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

