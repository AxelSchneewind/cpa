import ast

class StatementExtractor(ast.NodeTransformer):
    """
        Base class for NodeTransformers that extract statemnts from expressions
    """

    def __init__(self):
        self.instruction_stack = list()

    def push_instruction(self, instruction):
        assert isinstance(instruction, ast.AST)
        self.instruction_stack.append(instruction)

    def push_instruction_below(self, instruction):
        assert isinstance(instruction, ast.AST)
        self.instruction_stack.insert(0, instruction)

    def push_instructions(self, instructions):
        assert isinstance(instructions, list)
        assert all(not isinstance(i, list) for i in instructions)
        self.instruction_stack.extend(instructions)

    def push_instructions_below(self, instructions):
        assert isinstance(instructions, list)
        assert all(not isinstance(i, list) for i in instructions)
        self.instruction_stack.insert(0, instructions)
    
    def pop_instructions(self):
        current = list(reversed(self.instruction_stack))
        self.instruction_stack.clear()
        return current

    def visit_sequence(self, statements : list) -> list[ast.AST]:
        assert isinstance(statements, list)
        assert all(isinstance(s, ast.AST) for s in statements)

        result = list()
        for s in statements:
            expr = self.visit(s)
            result.extend(self.pop_instructions())
            if expr:
                result.append(expr)
            self.extract = False
            self.extract_expr = False

        assert all(isinstance(a, ast.AST) for a in result), result
        assert len(self.instruction_stack) == 0
        return result

    def fresh_tmp_var(self) -> ast.Name:
        var_name = '__tmp_' + str(self.current_tmp_ctr)
        self.current_tmp_ctr += 1
        return var_name


    def extract_expression(self, node, name=None) -> ast.Name:
        var_name = self.fresh_tmp_var() 

        self.push_instruction(self.assign_result_to(node, var_name))

        result = ast.Name(
            id = var_name,
            ctx = ast.Load(),
        )
        return result

    def extract_expression_last(self, node) -> ast.Name:
        var_name = '__tmp_' + str(self.current_tmp_ctr)
        self.current_tmp_ctr += 1

        self.push_instruction_below(self.assign_result_to(node, var_name))

        result = ast.Name(
            id = var_name,
            ctx = ast.Load(),
        )
        return result

    def visit_If(self, node) -> ast.If:
        body = self.visit_sequence(node.body)
        orelse = self.visit_sequence(node.orelse)

        self.extract = True
        test = self.visit(node.test)

        node.body = body
        node.orelse = orelse
        node.test = test
        return node

    def visit_While(self, node) -> ast.While:
        body = self.visit_sequence(node.body)

        self.extract = True
        test = self.visit(node.test)

        body.extend(self.instruction_stack)   # has to be recomputed for next test
        
        node.body = body
        node.test = test
        return node

    def visit_FunctionDef(self, node) -> ast.Module:
        body = self.visit_sequence(node.body)
        node.body = body
        return node

    def visit_Module(self, node) -> ast.Module:
        body = self.visit_sequence(node.body)
        node.body = body
        return node
