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
            case 'int':
                return node.args[0]
            case _:
                return node

    def visit_FunctionDef(self, node) -> ast.FunctionDef:
        """
            remove redefinitions
        """
        if node.name in self.builtin:
            return None
        else:
            return node

    def visit_Name(self, node) -> ast.Name:
        """
            rename variables that use __ prefix (marks verifier-internal identifiers)
        """
        if self.pattern.match(node.id):
            newname = ast.Name(
                id=str('USER') + node.id,
                ctx=node.ctx
            )
            ast.copy_location(newname, node)
            return newname
        else:
            return node
            



              