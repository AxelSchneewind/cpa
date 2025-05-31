from pycpa.ast import (
    ExpandAugAssign, ASTPreprocessor, EnsureReturn, RemoveBuiltins, 
    ASTVisualizer, SetExecutionContext, ExpandIfExp, ExpandReturn
)
from pycpa.cfa import builtin_identifiers

from pycpa import log

import ast

transformers = [
    EnsureReturn(),
    ExpandAugAssign(),
    ExpandReturn(),
    ExpandIfExp(),
    RemoveBuiltins(set(builtin_identifiers.keys())),
    ASTPreprocessor(),
]

def preprocess_ast(tree : ast.AST) -> ast.AST:
    for t in transformers:
        tree = t.visit(tree)
        tree = ast.fix_missing_locations(tree)
        try:
            ast.unparse(tree)
        except Exception as e:
            log.printer.log_debug(1, "Unparse failed after", t.__class__.__name__)
            raise e       # check if ast is valid, i.e. can be unparsed
    return tree 
