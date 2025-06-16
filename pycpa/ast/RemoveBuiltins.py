from typing import Optional

import ast
import re


class RemoveBuiltins(ast.NodeTransformer):
    """
        AST transformer that removes function definitions corresponding to builtin functions
    """


    def __init__(self, builtin_identifiers):
        self.builtin = builtin_identifiers
        self.pattern = re.compile(r'^__(tmp|ret)')

    def visit_Call(self, node) -> ast.Call:
        """
        removes call to int() as all variables are assumed to be integers
        """
        assert isinstance(node.func, ast.Name)
        name = node.func.id
        match name:
            case 'int' | 'float' | 'bool':
                return node.args[0]
            case _:
                return node

    def visit_FunctionDef(self, node) -> Optional[ast.FunctionDef]:
        """
            remove redefinitions
        """
        if node.name in self.builtin:
            return None
        else:
            return ast.NodeTransformer.generic_visit(self, node)

    def visit_AnnAssign(self, node) -> ast.AnnAssign:
        node.target = self.visit(node.target)
        return node



              
