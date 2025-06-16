import ast
from pycpa.ast.StatementExtractor import StatementExtractor

class ASTPreprocessor(StatementExtractor):
    """
        AST transformer that ensures a few desirable properties of the AST:
        Left sides of assignments are:
            - exactly one target (no compound assignments)
        Right sides of assignments are either: 
            - an arithmetic expression without function calls
            - exactly one function call
        Augmented assignments are expanded to ordinary ones.
        Arguments to function calls are:
            - Names
            - Constants
    """

    def __init__(self):
        StatementExtractor.__init__(self)

        # stores whether a visited call has to be extracted
        # always the case if not a single expression
        self.extract_call = False
        self.extract_expr = False

    def recurse(self, node, extract_call=False, extract_expr=False):
        # save old extraction flags
        old_extract_call = self.extract_call
        old_extract_expr = self.extract_expr

        self.extract_call = extract_call
        self.extract_expr = extract_expr
        result = self.visit(node)
        # restore old extraction flags
        self.extract_call = old_extract_call
        self.extract_expr = old_extract_expr
        return result

    def visit_BinOp(self, node):
        if not self.extract_expr:
            node.left  = self.recurse(node.left, extract_call=True)
            node.right = self.recurse(node.right, extract_call=True)
            return node
        return self.extract_expression(node)
    def visit_BoolOp(self, node):
        if not self.extract_expr:
            node.left  = self.recurse(node.left, extract_call=True)
            node.right = self.recurse(node.right, extract_call=True)
            return node
        return self.extract_expression(node)
    def visit_Compare(self, node):
        if not self.extract_expr:
            node.comparators = [self.recurse(c, extract_call=True) for c in node.comparators]
            return node
        return self.extract_expression(node)
    def visit_UnaryOp(self, node):
        if not self.extract_expr:
            node.operand = self.recurse(node.operand, extract_call=True)
            return node
        return self.extract_expression(node)

    def visit_Call(self, node: ast.Call) -> ast.Name | ast.Call:
        do_extract = self.extract_call
        self.extract_call = True
        self.extract_expr = True

        call = ast.Call(
            func=node.func,
            args=[self.recurse(arg, extract_call=True, extract_expr=True) for arg in node.args]
        )
        ast.copy_location(call, node)
        ast.fix_missing_locations(call)

        if do_extract:
            # here, the instruction for this call has to be put under the instructions of the args
            head = self.extract_expression_last(call)
            ast.copy_location(head, node)
            ast.fix_missing_locations(head)

            return head
        else:       
            # call can be kept in place
            return call

    def visit_Assign(self, node) -> ast.Assign:
        target, value = node.targets[0], node.value
        assert isinstance(node.targets[0], ast.Name)

        # simple expression can be kept
        self.extract_call = not (isinstance(value, ast.Name) or isinstance(value, ast.Constant) or isinstance(value, ast.Call))
        self.extract_expr = False

        right = self.visit(value)
        left  = self.visit(target)

        head = ast.Assign([left], right)
        ast.copy_location(head, node)
        ast.fix_missing_locations(head)

        return head

             