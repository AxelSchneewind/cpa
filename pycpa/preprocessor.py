from pycpa.ast import (
    ExpandAugAssign, ASTPreprocessor, EnsureReturn, RemoveBuiltins, 
    ASTVisualizer, SetExecutionContext, ExpandIfExp, ExpandReturn
)
from pycpa.cfa import builtin_identifiers

import ast

transformers = [
    EnsureReturn(),
    ExpandAugAssign(),
    ExpandReturn(),
    ExpandIfExp(),
    RemoveBuiltins(set(builtin_identifiers.keys())),
    ASTPreprocessor(),
]

# def preprocess_ast(tree : ast.AST) -> ast.AST:
#     for t in transformers:
#         tree = t.visit(tree)
#         tree = ast.fix_missing_locations(tree)
#         print("Tree: ", tree)
#         try:
#             ast.unparse(tree)
#         except Exception as e:
#             print("Unparse failed after", t.__class__.__name__)
#             raise e       # check if ast is valid, i.e. can be unparsed
#     return tree 

def preprocess_ast(tree: ast.AST) -> ast.AST:
    for t in transformers:
        tree = t.visit(tree)
        tree = FixMissingKeywords().visit(tree)
        tree = ast.fix_missing_locations(tree)
        try:
            ast.unparse(tree)  # check if AST is valid
        except Exception as e:
            print("Unparse failed after", t.__class__.__name__)
            raise e
    return tree


class FixMissingKeywords(ast.NodeTransformer):
    def visit_Call(self, node):
        self.generic_visit(node)
        if not hasattr(node, 'keywords'):
            node.keywords = []
        return node
