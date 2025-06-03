import ast
from pycpa.ast.StatementExtractor import StatementExtractor

class CallAssignToRet(StatementExtractor):
    """
    """

    def __init__(self):
        StatementExtractor.__init__(self)

    def visit_Assign(self, node) -> ast.Assign:
        target, value = node.targets[0], node.value
        assert isinstance(node.targets[0], ast.Name)

        if not isinstance(value, ast.Call) or target.id == '__ret':
            return node

        var_store = ast.Name('__ret', ast.Store())
        assign = ast.Assign(
            [var_store], node.value
        )
        ast.copy_location(assign, node)
        ast.fix_missing_locations(assign)
        self.push_instruction(assign)

        var_load = ast.Name('__ret', ast.Load())
        head = ast.Assign([target], var_load)
        ast.copy_location(head, node)
        ast.fix_missing_locations(head)

        return head

             