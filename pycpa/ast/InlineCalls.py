import ast
from pycpa.ast.StatementExtractor import StatementExtractor

from pycpa.cfa import builtin_identifiers

class InlineCalls(StatementExtractor):
    """
    """

    def __init__(self):
        StatementExtractor.__init__(self)
        self.current_function = None
        self.function_def = {}
        self.return_variable = {}


    def visit_FunctionDef(self, node : ast.FunctionDef) -> ast.FunctionDef:
        if node.name in builtin_identifiers:
            return node

        # 
        self.function_def[node.name] = node
        self.current_function = node.name

        ast.NodeVisitor.generic_visit(self, node)

        self.current_function = None
        return None
    
    def visit_Return(self, node) -> ast.Assign | None:
        if node.value:  # assign to return variable
            assign = ast.Assign(
                [ast.Name('__ret', ctx=ast.Load())],
                node.value
            )
            ast.copy_location(assign, node)
            ast.fix_missing_locations(assign)
            return assign
        else:
            return None # remove return

    def visit_Call(self, node) -> ast.Name | ast.Call:
        if node.func.id not in builtin_identifiers and node.func.id in self.function_def:
            self.push_instructions(self.function_def[node.func.id].body)
            name = ast.Name('__ret', ctx=ast.Load())
            ast.copy_location(name, node)
            ast.fix_missing_locations(name)
            return name
        else:
            return node

    def visit_Assign(self, node) -> ast.Assign:
        target, value = node.targets[0], node.value

        if not isinstance(value, ast.Call):
            return node

        node.value = self.visit(value)
        return node

             