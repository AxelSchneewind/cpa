import ast
from ast import AST


class EnsureReturn(ast.NodeTransformer):
    """
        AST transformer that ensures that each function ends with a return statement
    """

    def visit_FunctionDef(self, node) -> ast.FunctionDef:
        if isinstance(node.body[-1], ast.Pass):
            ret = ast.Return()
            ast.copy_location(ret, node)
            node.body[-1] = ret
            return node
        if not isinstance(node.body[-1], ast.Return):
            ret = ast.Return()
            ast.copy_location(ret, node)
            node.body.append(ret)
            return node

              