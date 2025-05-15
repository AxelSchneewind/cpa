import ast

class ASTPreprocessor(ast.NodeTransformer):
    """
        AST transformer that ensures a few desirable properties of the AST:
        Left sides of assignments are:
            - exactly one target (no compound assignments)
        Right sides of assignments are either: 
            - an arithmetic expression without function calls
            - exactly one function call
        Augmented assignments are expanded to ordinary ones.
    """

    def __init__(self):
        self.instruction_stack = list()
        self.current_tmp_ctr = 0
        self.extract = False

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
        self.current_tmp_ctr = 0
        return current

    def visit_sequence(self, statements : list) -> list[ast.AST]:
        result = list()
        for s in statements:
            expr = self.visit(s)
            result.extend(self.pop_instructions())
            result.append(expr)
            self.extract = False

        assert all(isinstance(a, ast.AST) for a in result), result
        return result


    def assign_result_to(self, call : ast.Call, return_var : str) -> ast.AST:
        assert isinstance(call, ast.Call)
        expr = ast.Assign(
            targets = [ast.Name(return_var, ctx=ast.Store())],
            value = call
        )
        ast.copy_location(call, expr)
        ast.fix_missing_locations(expr)
        return expr

    def visit_Call(self, node: ast.Call) -> ast.Name:
        do_extract = self.extract

        var_name = '__tmp_' + str(self.current_tmp_ctr)
        self.current_tmp_ctr += 1
        self.extract = True

        call = ast.Call(
            func=node.func,
            args=[self.visit(arg) for arg in node.args]
        )

        if do_extract:
            # here, the instruction for this call has to be put under the instructions of the args
            self.push_instruction_below(self.assign_result_to(call, var_name))

            head = ast.Name(var_name, ctx=ast.Load())
            ast.copy_location(head, node)
            ast.fix_missing_locations(head)

            return head
        else:       
            # call can be kept in place
            return call

    def visit_Assign(self, node) -> ast.Assign:
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

        # complex expression: extract calls
        if not isinstance(value, ast.Call):
            self.extract = True

        right = self.visit(value)

        self.extract = False
        left  = self.visit(target)

        head = ast.Assign([left], right)
        ast.copy_location(head, node)
        ast.fix_missing_locations(head)

        return head

    def visit_AugAssign(self, node) -> ast.AugAssign:
        assign = ast.Assign(
            targets =[node.target], 
            value = ast.BinOp([node.target], node.op, node.value)
        )
        ast.copy_location(assign, node)
        ast.fix_missing_locations(assign)

        return self.visit(assign)

   
    def visit_If(self, node) -> ast.If:
        body = self.visit_sequence(node.body)
        orelse = self.visit_sequence(node.orelse)

        test = self.visit(node.test)

        head = ast.If(test, body, orelse)
        ast.copy_location(head, node)
        ast.fix_missing_locations(head)

        return head

    def visit_While(self, node) -> ast.While:
        test = self.visit(node.test)
        test_instructions = list(self.instruction_stack)

        body = self.visit_sequence(node.body)
        body.extend(test_instructions)   # has to be recomputed for next test

        head = ast.While(test, body)
        ast.copy_location(head, node)
        ast.fix_missing_locations(head)

        return head

    def visit_Module(self, node) -> ast.Module:
        body = self.visit_sequence(node.body)
        return ast.Module(body)
              