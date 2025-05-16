import ast
from ast import AST


class EnsureReturn(ast.NodeTransformer):
    """
        AST transformer that ensures that each function ends with a return statement
    """

    def visit_FunctionDef(self, node) -> ast.FunctionDef:
        assert len(node.body) > 0
        match node.body[-1]:
            case ast.Return():
                return node
            case ast.Pass():
                ret = ast.Return()
                ast.copy_location(ret, node)
                node.body[-1] = ret
                return node
            case _:
                ret = ast.Return()
                ast.copy_location(ret, node)
                node.body.append(ret)
                return node
        

              