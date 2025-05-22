from pycpa.ast import (
    ExpandAugAssign, ASTPreprocessor, EnsureReturn, RemoveBuiltins, 
    ASTVisualizer, SetExecutionContext, ExpandIfExp
)
from pycpa.cfa import builtin_identifiers

import ast

transformers = [
    ExpandAugAssign(),
    ExpandIfExp(),
    RemoveBuiltins(set(builtin_identifiers.keys())),
    EnsureReturn(),
    ASTPreprocessor(),
]

def preprocess_ast(tree : ast.AST) -> ast.AST:
    for t in transformers:
        tree = t.visit(tree)
        ast.unparse(tree)       # check if ast is valid, i.e. can be unparsed
    return tree

