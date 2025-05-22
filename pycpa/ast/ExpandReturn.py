import ast
import re
import copy

from pycpa.ast.StatementExtractor import StatementExtractor

class ExpandReturn(StatementExtractor):
    """
        AST transformer that transform a value-return into assignment and return
    """

    def __init__(self):
        StatementExtractor.__init__(self)
        

    def visit_Return(self, node) -> ast.Return:
        if node.value is None:
            return node

        varname = '__ret'
        ret = ast.Return(
            ast.Name(varname, ast.Load())
        )
        ast.copy_location(ret, node)
        ast.fix_missing_locations(ret)

        assign = ast.Assign(
            targets = [ ast.Name(varname, ast.Store()) ],
            value   = node.value
        )
        ast.copy_location(assign, node)
        ast.fix_missing_locations(assign)
        self.push_instruction(assign)

        return ret