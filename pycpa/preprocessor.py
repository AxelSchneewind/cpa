from pycpa.ast import ExpandAugAssign, ASTPreprocessor, EnsureReturn, RemoveBuiltins, ASTVisualizer, SetExecutionContext
from pycpa.cfa import builtin_identifiers

import ast

transformers = [
    ExpandAugAssign(),
    RemoveBuiltins(set(builtin_identifiers.keys())),
    SetExecutionContext(),
    EnsureReturn(),
    ASTPreprocessor(),
]

def preprocess_ast(tree : ast.AST) -> ast.AST:
    for t in transformers:
        tree = t.visit(tree)
    return tree

