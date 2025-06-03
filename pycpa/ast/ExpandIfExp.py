from pycpa.ast.StatementExtractor import StatementExtractor

from typing import Optional

import ast

class ExpandIfExp(StatementExtractor):
    """
        AST transformer that transforms IfExps (ternary expressions)
        into statements
    """

    def __init__(self):
        StatementExtractor.__init__(self)

    def assign_result_to(self, call : ast.AST, return_var : str) -> ast.Assign:
        expr = ast.Assign(
            targets = [ast.Name(return_var, ctx=ast.Store())],
            value = call
        )
        ast.copy_location(call, expr)
        ast.fix_missing_locations(expr)
        return expr


    def visit_IfExp(self, node: ast.IfExp) -> ast.Name:
        # if not already handled by assign: use temporary variable
        name = self.fresh_tmp_var()
        branch = ast.If(
            test=node.test,
            body=[ast.Assign([ast.Name(name, ctx=ast.Store())], self.visit(node.body))],
            orelse=[ast.Assign([ast.Name(name, ctx=ast.Store())], self.visit(node.orelse))]
        )
        ast.copy_location(branch, node)
        ast.fix_missing_locations(branch)

        return self.extract_expression(branch)

    def visit_Assign(self, node: ast.Assign) -> Optional[ast.Assign]:
        if not isinstance(node.value, ast.IfExp):
            return node

        branch = ast.If(
            test=node.value.test,
            body=[ast.Assign(node.targets, self.visit(node.value.body))],
            orelse=[ast.Assign(node.targets, self.visit(node.value.orelse))]
        )
        ast.copy_location(branch, node)
        ast.fix_missing_locations(branch)

        self.push_instruction(branch)
        return None
            