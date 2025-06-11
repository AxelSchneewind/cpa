import ast

class ASTChecker(ast.NodeVisitor):
    """
        Checks a set of desirable properties of the AST used for program analysis

        This class can also be considered as documentation for handling python expressions in program analysis
    """

    def __init__(self):
        pass

    def _assert(condition):
        assert condition
    def _assert_type(obj, t : type | tuple[type]):
        assert isinstance(obj, t), obj
    def _assert_types(objs, t : type | tuple[type]):
        assert all(isinstance(obj, t) for obj in objs), objs

    def visit_Constant(self, node):
        self._assert_type(node.value, (int, str)), node.value
        ast.NodeVisitor.generic_visit(self, node)

    def visit_Name(self, node):
        ast.NodeVisitor.generic_visit(self, node)

    def visit_Subscript(self, node):
        ast.NodeVisitor.generic_visit(self, node)

    def visit_BinOp(self, node):
        self._assert_type(node.left, (ast.Name, ast.Constant)), node.left
        self._assert_type(node.right, (ast.Name, ast.Constant)), node.right
        ast.NodeVisitor.generic_visit(self, node)

    def visit_Compare(self, node):
        self._assert_types(c, (ast.Name, ast.Constant))
        self._assert(len(node.ops) == 1)
        ast.NodeVisitor.generic_visit(self, node)

    def visit_UnaryOp(self, node):
        self._assert_type(node.operand, (ast.Name, ast.Constant)), node.operand
        ast.NodeVisitor.generic_visit(self, node)

    def visit_Call(self, node: ast.Call):
        self._assert_types(a, (ast.Name, ast.Constant))
        self._assert_type(node.func, ast.Name), node.func
        ast.NodeVisitor.generic_visit(self, node)

    def visit_Assign(self, node):
        self._assert(len(node.targets) == 1)
        self._assert_type(node.targets[0], (ast.Name, ast.Subscript)), node.targets[0]
        ast.NodeVisitor.generic_visit(self, node)

    def visit_AugAssign(self, node):
        self._assert(False)

             
