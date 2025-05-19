# from pycpa.ast import ExpandAugAssign, ASTPreprocessor, EnsureReturn, RemoveBuiltins, ASTVisualizer, SetExecutionContext
# from pycpa.cfa import builtin_identifiers

# import ast

# transformers = [
#     ExpandAugAssign(),
#     RemoveBuiltins(set(builtin_identifiers.keys())),
#     SetExecutionContext(),
#     EnsureReturn(),
#     ASTPreprocessor(),
# ]

# def preprocess_ast(tree : ast.AST) -> ast.AST:
#     for t in transformers:
#         tree = t.visit(tree)
#     return tree

from pycpa.ast import (
    ExpandAugAssign, ASTPreprocessor, EnsureReturn,
    RemoveBuiltins, ASTVisualizer, SetExecutionContext
)
from pycpa.cfa import builtin_identifiers

import ast

transformers = [
    ExpandAugAssign(),
    RemoveBuiltins(set(builtin_identifiers.keys())),
    SetExecutionContext(),
    EnsureReturn(),
    ASTPreprocessor(),
]

def preprocess_ast(tree: ast.AST) -> ast.AST:
    # run the normal passes
    for t in transformers:
        tree = t.visit(tree)

    # --------------------------------------------------------------
    # *FIX*: ensure every ast.Call has .keywords (list) attribute
    # --------------------------------------------------------------
    for node in ast.walk(tree):
        if isinstance(node, ast.Call) and not hasattr(node, "keywords"):
            node.keywords = []           # repair in place

    return tree
