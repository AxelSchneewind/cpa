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
        self.extract = False
        self.extract_expr = False

    def assign_result_to(self, call : ast.AST, return_var : str) -> ast.AST:
        expr = ast.Assign(
            targets = [ast.Name(return_var, ctx=ast.Store())],
            value = call
        )
        ast.copy_location(call, expr)
        ast.fix_missing_locations(expr)
        return expr


    def visit_BinOp(self, node):
        if not self.extract_expr:
            return node
        return self.extract_expression(node)
    def visit_BoolOp(self, node):
        if not self.extract_expr:
            return node
        return self.extract_expression(node)
    def visit_Compare(self, node):
        if not self.extract_expr:
            return node
        return self.extract_expression(node)
    def visit_UnaryOp(self, node):
        if not self.extract_expr:
            return node
        return self.extract_expression(node)

    def visit_Call(self, node: ast.Call) -> ast.Name:
        do_extract = self.extract
        self.extract = True
        self.extract_expr = True

        call = ast.Call(
            func=node.func,
            args=[self.visit(arg) for arg in node.args]
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
        self.extract = True
        target, value = node.targets[0], node.value

        if (isinstance(node.targets[0], ast.Tuple) and isinstance(node.value, ast.Tuple)):
            if len(node.targets[0].elts) == len(node.value.elts) > 1:
                target, value = node.targets[0].elts.pop(), node.value.elts.pop()
            
                right = self.visit(value)
                left  = self.visit(target) 
                assign = ast.Assign(
                    targets=[left],
                    value=right
                )
                ast.copy_location(assign, node)
                ast.fix_missing_locations(assign)

                result = self.visit(assign)
                self.push_instruction_below(result)

                return self.visit(node)

            else:
                target, value = node.targets[0].elts[0], node.value.elts[0]

        right = self.visit(value)
        left  = self.visit(target)

        head = ast.Assign([left], right)
        ast.copy_location(head, node)
        ast.fix_missing_locations(head)

        return head

             