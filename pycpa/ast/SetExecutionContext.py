import ast
import re

class SetExecutionContext(ast.NodeTransformer):
    """
        AST transformer that defines relevant python-builtins
    """

    def __init__(self):
        pass

    def visit_Module(self, node) -> ast.FunctionDef:
        statement = ast.Assign(
            [ast.Name('__name__', ast.Store())],
            ast.Constant('__name__')
        )

        if len(node.body) > 0:
            ast.copy_location(statement, node.body[0])
        else:
            ast.copy_location(statement, node)
        ast.fix_missing_locations(statement)

        node.body.insert(0, statement)
        return node
              




