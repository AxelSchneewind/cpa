from pycpa.ast import (
    ExpandAugAssign, ASTPreprocessor, EnsureReturn, RemoveBuiltins, 
    ASTVisualizer, SetExecutionContext, ExpandIfExp, ExpandReturn,
    EnsureScoping, CallAssignToRet
)
from pycpa.cfa import builtin_identifiers

from pycpa import log

import ast

transformers = [
    EnsureScoping(),
    EnsureReturn(),
    ExpandAugAssign(),
    ExpandReturn(),
    ExpandIfExp(),
    RemoveBuiltins(set(builtin_identifiers.keys())),
    ASTPreprocessor(),
    CallAssignToRet(),
]

def preprocess_ast(tree : ast.AST) -> ast.AST:
    for t in transformers:
        tree = t.visit(tree)
        tree = ast.fix_missing_locations(tree)
    return tree 
