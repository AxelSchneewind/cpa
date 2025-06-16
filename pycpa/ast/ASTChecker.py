import ast

class ASTChecker(ast.NodeVisitor):
    """
        Checks a set of desirable properties of the AST used for program analysis

        This class can also be considered as documentation for handling python expressions in program analysis
    """

    def __init__(self):
        pass

    def _assert(self, condition):
        assert condition
    def _assert_type(self, obj, t : type | tuple[type]):
        assert isinstance(obj, t), obj
    def _assert_types(self, objs, t : type | tuple[type]):
        assert all(isinstance(obj, t) for obj in objs), objs

    def _assert_type_arithmetic(self, obj):
        self._assert_type(obj,  (ast.Name, ast.Constant, ast.UnaryOp, ast.BinOp, ast.Compare, ast.BoolOp))
    def _assert_types_arithmetic(self, obj):
        self._assert_types(obj, (ast.Name, ast.Constant, ast.UnaryOp, ast.BinOp, ast.Compare, ast.BoolOp))

    def _assert_type_rvalue(self, obj):
        self._assert_type(obj, (ast.Name, ast.Constant, ast.UnaryOp, ast.BinOp, ast.Compare, ast.BoolOp, ast.Call))
    def _assert_type_lvalue(self, obj):
        self._assert_type(obj, (ast.Name, ast.Subscript))


    def visit_Constant(self, node):
        self._assert_type(node.value, (int, str))
        ast.NodeVisitor.generic_visit(self, node)

    def visit_Name(self, node):
        ast.NodeVisitor.generic_visit(self, node)

    def visit_Subscript(self, node):
        ast.NodeVisitor.generic_visit(self, node)

    def visit_BinOp(self, node):
        self._assert_type_arithmetic(node.left)
        self._assert_type_arithmetic(node.right)
        ast.NodeVisitor.generic_visit(self, node)

    def visit_Compare(self, node):
        self._assert_types_arithmetic(node.comparators)
        self._assert(len(node.ops) == 1)
        ast.NodeVisitor.generic_visit(self, node)

    def visit_UnaryOp(self, node):
        self._assert_type_arithmetic(node.operand)
        ast.NodeVisitor.generic_visit(self, node)

    def visit_Call(self, node: ast.Call):
        self._assert_types(node.args, (ast.Name, ast.Constant))
        self._assert_type(node.func, ast.Name)
        ast.NodeVisitor.generic_visit(self, node)

    def visit_Assign(self, node):
        self._assert(len(node.targets) == 1)
        self._assert_type_lvalue(node.targets[0])
        self._assert_type_rvalue(node.value)
        ast.NodeVisitor.generic_visit(self, node)

    def visit_AugAssign(self, node):
        self._assert(False)

             
