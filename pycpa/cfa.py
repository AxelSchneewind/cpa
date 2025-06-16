#!/usr/bin/env python

from typing import List, Self
from enum import Enum

from graphviz import Digraph
import ast

from pycpa import log



class CFANode:
    index = 0

    def __init__(self):
        self.node_id = CFANode.index
        self.entering_edges = list()
        self.leaving_edges = list()
        CFANode.index += 1

    def __str__(self):
        return "(%s)" % str(self.node_id)

    @staticmethod
    def merge(a : 'CFANode', b : 'CFANode') -> 'CFANode':
        for entering_edge in b.entering_edges:
            entering_edge.successor = a
            a.entering_edges.append(entering_edge)
        for leaving_edge in b.leaving_edges:
            leaving_edge.predecessor = a
            a.leaving_edges.append(leaving_edge)
        b.entering_edges = list()
        b.leaving_edges = list()
        if CFANode.index == b.node_id + 1:
            CFANode.index -= 1
        return a


class TraverseCFA:
    @staticmethod
    def bfs_edges(root: CFANode):
        waitlist : set[CFANode] = set()
        waitlist.add(root)

        seen : set[CFANode] = set()

        while len(waitlist) > 0:
            n = waitlist.pop()

            if n in seen:
                continue

            for e in n.leaving_edges:
                yield e
            seen.add(n)

            # collect successors
            waitlist.update({e.successor for e in n.leaving_edges})

    @staticmethod
    def bfs(root: CFANode):
        waitlist : set[CFANode] = set()
        waitlist.add(root)

        seen : set[CFANode] = set()

        while len(waitlist) > 0:
            n = waitlist.pop()

            if n in seen:
                continue

            yield n
            seen.add(n)

            # collect successors
            waitlist.update({e.successor for e in n.leaving_edges})
            


class InstructionType(Enum):
    STATEMENT = 1,
    ASSUMPTION = 2,
    CALL = 3,
    RETURN = 4,
    RESUME = 5,
    NONDET = 6,
    EXIT = 7,
    ABORT = 8,
    REACH_ERROR = 9,
    EXTERNAL = 10,
    NOP = 11

builtin_identifiers = {
    'exit'                          : InstructionType.EXIT,
    'abort'                         : InstructionType.ABORT,
    'call'                          : InstructionType.CALL,
    'return'                        : InstructionType.RETURN,
    'nondet'                        : InstructionType.NONDET,
    '__VERIFIER_nondet_char'        : InstructionType.NONDET,
    '__VERIFIER_nondet_short'       : InstructionType.NONDET,
    '__VERIFIER_nondet_int'         : InstructionType.NONDET,
    '__VERIFIER_nondet_long'        : InstructionType.NONDET,
    '__VERIFIER_nondet_uchar'       : InstructionType.NONDET,
    '__VERIFIER_nondet_ushort'      : InstructionType.NONDET,
    '__VERIFIER_nondet_uint'        : InstructionType.NONDET,
    '__VERIFIER_nondet_ulong'       : InstructionType.NONDET,
    'reach_error'                   : InstructionType.REACH_ERROR,
}

class Instruction:
    """
    An instruction can have different types, the most important ones being 
     - statements
     - assumptions
     - calls (to defined functions or builtins)
     - reacherror
    """

    def __init__(self, expression, kind=InstructionType.STATEMENT, **params):
        self.kind = kind
        self.expression = expression
        for p, p_val in params.items():
            if not hasattr(self, p):
                setattr(self, p, p_val)
    
    def __str__(self):
        identifier = str(self.kind).replace('InstructionType.', '')
        match self.kind:
            case InstructionType.EXIT:
                code = self.exit_code if 'exit_code' in self.parameters else '0'
                return '%s(%s)' % (identifier, code)
            case InstructionType.CALL:
                return 'jump %s' % (self.location)
            case _:
                return '%s' % self.identifier


    @staticmethod
    def assumption(expression, negated=False):
        if negated:
            expression = ast.UnaryOp(op=ast.Not(), operand=expression,
                lineno=expression.lineno, col_offset=expression.col_offset
            )
        return Instruction(expression, kind=InstructionType.ASSUMPTION, negated=negated)

    @staticmethod
    def statement(expression):
        return Instruction(expression)

    @staticmethod
    def builtin(expression : ast.Call, target_variable : str = '__ret', **params):
        assert isinstance(expression, ast.Call)
        # Ensure expression.func is an ast.Name node before accessing .id
        name = ""
        if isinstance(expression.func, ast.Name):
            name = str(expression.func.id)
        else:
            # Handle cases where func is not a simple name (e.g., attribute access)
            # For simplicity, we might raise an error or return a generic instruction
            log.printer.log_debug(1, f"[Instruction WARN] Builtin call to non-Name func: {ast.dump(expression.func)}. Treating as EXTERNAL.")
            return Instruction(expression, kind=InstructionType.EXTERNAL, target_variable=target_variable, **params)

        assert name in builtin_identifiers, f"Builtin '{name}' not recognized."
        return Instruction(expression, kind=builtin_identifiers[name], target_variable=target_variable, **params)

    @staticmethod
    def reacherror(expression, **params):
        return Instruction(expression, kind=InstructionType.REACH_ERROR, **params)

    @staticmethod
    def ret(expression : ast.Return):
        assert isinstance(expression, ast.Return)
        return Instruction(expression, kind=InstructionType.RETURN)

    @staticmethod
    def call(expression : ast.Call, declaration : ast.FunctionDef, entry_point : CFANode, argnames : List[ast.Name | ast.Constant], **params):
        param_names = []
        for p in declaration.args.args:
            assert isinstance(p.arg, str), type(p.arg)
            param_names.append(p.arg)

        args = []
        for a in argnames:
            assert isinstance(a, ast.Name) or isinstance(a, ast.Constant), (a, type(a))
            args.append(a)

        return Instruction(
            expression, 
            kind=InstructionType.CALL, 
            location=entry_point, 
            declaration=declaration, 
            param_names=param_names, 
            arg_names=args, 
            **params
        )

    @staticmethod
    def nop(expression):
        return Instruction(expression, kind=InstructionType.NOP)


class CFAEdge:
    def __init__(self, predecessor, successor, instruction):
        self.predecessor = predecessor
        self.successor = successor
        predecessor.leaving_edges.append(self)
        successor.entering_edges.append(self)
        self.instruction = instruction

    def __str__(self):
        return "%s -%s-> %s" % (
            str(self.predecessor),
            self.label(),
            str(self.successor),
        )

    def label(self) -> str:
        if self.instruction.kind == InstructionType.ASSUMPTION:
            return str(self.instruction.expression.lineno) + ': [' + ast.unparse(self.instruction.expression).strip() + ']'
        elif self.instruction.kind == InstructionType.STATEMENT:
            return str(self.instruction.expression.lineno) + ': ' + ast.unparse(self.instruction.expression).strip()
        elif self.instruction.kind == InstructionType.CALL:
            return str(self.instruction.expression.lineno) + ': ' + self.instruction.declaration.name.strip() + '()'
        elif self.instruction.kind == InstructionType.RETURN:
            return str(self.instruction.expression.lineno) + ': ' + ast.unparse(self.instruction.expression).strip()
        else:
            return '< %s >' % self.instruction.kind


class CFACreator(ast.NodeVisitor):
    def __init__(self):
        self.global_root = CFANode()
        self.entry_point = self.global_root
        self.roots = [self.global_root]
        self.node_stack = list()
        self.node_stack.append(self.global_root)
        self.continue_stack = list()
        self.break_stack = list()
        # function name to ast.FunctionDef 
        self.function_def = {}
        # function name to entry-point CFANode
        self.function_entry_point = {}

        self.inline = False

    def visit_FunctionDef(self, node : ast.FunctionDef):
        pre = self.node_stack.pop()

        # for continuing after definition 
        post = CFANode()
        edge = CFAEdge(pre, post, Instruction.nop(node))
        self.node_stack.append(post)

        # ignore definitions of builtin functions
        if node.name in builtin_identifiers:
            print('Warning: builtin', node.name, 'redefined, ignoring')
            return

        # 
        root = CFANode()
        self.function_def[node.name] = node
        self.function_entry_point[node.name] = root

        if node.name == 'main':
            self.entry_point = root

        self.node_stack.append(root)
        self.roots.append(root)
        ast.NodeVisitor.generic_visit(self, node)

        # final return statement is guaranteed, remove its exit node
        self.node_stack.pop()

    def visit_While(self, node : ast.While):
        entry_node = self.node_stack.pop()
        inside = CFANode()
        self.continue_stack.append(entry_node)
        edge = CFAEdge(entry_node, inside, Instruction.assumption(node.test))
        outside = CFANode()
        self.break_stack.append(outside)
        edge = CFAEdge(
            entry_node, outside, Instruction.assumption(node.test, negated=True)
        )
        self.node_stack.append(inside)
        for statement in node.body:
            self.visit(statement)
        body_exit_node = self.node_stack.pop()
        CFANode.merge(entry_node, body_exit_node)
        self.node_stack.append(outside)
        self.continue_stack.pop()
        self.break_stack.pop()

    def visit_Break(self, node : ast.Break):
        entry_node = self.node_stack.pop()
        next_node = CFANode()            # create node for next line after break

        # make edge from entry node to break node
        edge = CFAEdge(
            entry_node, self.break_stack[-1], Instruction.statement(node)
        )

        self.node_stack.append(next_node)

    def visit_Continue(self, node : ast.Continue):
        entry_node = self.node_stack.pop()
        next_node = CFANode()             # create node for next line after break

        # make edge from entry node to continue node
        edge = CFAEdge(
            entry_node, self.continue_stack[-1], Instruction.statement(node)
        )

        self.node_stack.append(next_node)

    def visit_If(self, node : ast.If):
        entry_node = self.node_stack.pop()
        left = CFANode()
        edge = CFAEdge(
            entry_node, left, Instruction.assumption(node.test)
        )
        right = CFANode()
        edge = CFAEdge(
            entry_node, right, Instruction.assumption(node.test, negated=True)
        )
        self.node_stack.append(left)
        for statement in node.body:
            self.visit(statement)
        left_exit = self.node_stack.pop()
        self.node_stack.append(right)
        for statement in node.orelse:
            self.visit(statement)
        right_exit = self.node_stack.pop()
        merged_exit = CFANode.merge(left_exit, right_exit)
        self.node_stack.append(merged_exit)

    def visit_Expr(self, node : ast.Expr):
        self.visit(node.value)

    def visit_Assign(self, node : ast.Assign):
        if isinstance(node.value, ast.Call):
            assert isinstance(node.targets[0], ast.Name)

            target_var_name = node.targets[0].id
            call = node.value
            if self.inline:
                self._handle_Call_inline(call, target_var_name)
            else:
                self._handle_Call(call, target_var_name)
        else:
            entry_node = self.node_stack.pop()
            exit_node = CFANode()
            edge = CFAEdge(entry_node, exit_node, Instruction.statement(node))
            self.node_stack.append(exit_node)

    def visit_Return(self, node : ast.Return):
        assert node.value is None or isinstance(node.value, ast.Name) or isinstance(node.value, ast.Constant), node.value
        val = node.value

        entry_node = self.node_stack.pop()
        exit_node = CFANode()
        edge = CFAEdge(entry_node, exit_node, Instruction.ret(node))
        self.node_stack.append(exit_node)

    def _handle_Call_inline(self, call_node : ast.Call, target_variable : str | None = None):
        assert isinstance(call_node, ast.Call), call_node
        assert isinstance(call_node.func, ast.Name), call_node  # function could be attribute (e.g. member functions), not supported

        if call_node.func.id not in builtin_identifiers and call_node.func.id not in self.function_def and call_node.func.id not in self.function_entry_point:
            print('Warning: call to undefined', ast.unparse(call_node.func))
            return

        arg_names = []
        for i, val in enumerate(call_node.args):
            assert isinstance(val, ast.Name) or isinstance(val, ast.Constant)
            arg_names.append(val)

        # make builtin edge
        if call_node.func.id in builtin_identifiers:
            entry_node = self.node_stack.pop()
            exit_node = CFANode()
            edge = CFAEdge(entry_node, exit_node, Instruction.builtin(call_node, target_variable=target_variable))
            self.node_stack.append(exit_node)
        else:
            for formal, arg in zip(self.function_def[call_node.func.id].args.args, arg_names):
                if formal != arg:
                    assign = ast.Assign(
                        targets=[ast.Name( formal.arg, ctx=ast.Store() )],
                        value= arg
                    )
                    ast.copy_location(assign, call_node)
                    ast.fix_missing_locations(assign)
                    self.visit(assign)
            for b in self.function_def[call_node.func.id].body:
                if isinstance(b, ast.Return) and target_variable:
                    if target_variable and b.value and (not isinstance(b.value, ast.Name) or b.value.id != target_variable):
                        assign = ast.Assign(
                            targets=[ast.Name(target_variable, ctx=ast.Store() )],
                            value=b.value
                        )
                        ast.copy_location(assign, call_node)
                        ast.fix_missing_locations(assign)
                        self.visit(assign)
                else:
                    self.visit(b)




    def _handle_Call(self, call_node : ast.Call, target_variable : str ='__ret'):
        assert isinstance(call_node, ast.Call), call_node
        assert isinstance(call_node.func, ast.Name), call_node  # function could be attribute (e.g. member functions), not supported

        if call_node.func.id not in builtin_identifiers and call_node.func.id not in self.function_def and call_node.func.id not in self.function_entry_point:
            print('Warning: call to undefined', ast.unparse(call_node.func))
            return

        # add computing edge for each argument
        arg_names = []
        for i, val in enumerate(call_node.args):
            assert isinstance(val, ast.Name) or isinstance(val, ast.Constant)
            arg_names.append(val)

        # make builtin edge
        if call_node.func.id in builtin_identifiers:
            entry_node = self.node_stack.pop()
            exit_node = CFANode()
            edge = CFAEdge(entry_node, exit_node, Instruction.builtin(call_node, target_variable=target_variable))
            self.node_stack.append(exit_node)
        else:
            entry_node = self.node_stack.pop()
            exit_node = CFANode()

            instruction = Instruction.call(call_node, self.function_def[call_node.func.id], self.function_entry_point[call_node.func.id], arg_names)
            edge = CFAEdge(entry_node, exit_node, instruction)
            self.node_stack.append(exit_node)

    def visit_Call(self, node : ast.Call):
        if self.inline:
            return self._handle_Call_inline(node)
        else:
            return self._handle_Call(node)

    def visit_Assert(self, node : ast.Assert):
        raise NotImplementedError('TODO: convert to __VERIFIER_assert in preprocessing')

    def visit_Raise(self, node : ast.Raise):
        # make reacherror edge, i.e. exceptions are used like reacherror()
        entry_node = self.node_stack.pop()
        exit_node = CFANode()
        edge = CFAEdge(entry_node, exit_node, Instruction.reacherror(node))
        self.node_stack.append(exit_node)


class Graphable:
    def get_node_label(self):
        pass

    def get_edge_labels(self, other):
        pass

    def get_successors(self):
        pass

class GraphableCFANode(Graphable):
    def __init__(self, node):
        assert isinstance(node, CFANode)
        self.node = node

    def get_node_label(self):
        return str(self.node.node_id)

    def get_edge_labels(self, other):
        return [
            edge.label()
            for edge in self.node.leaving_edges
            if edge.successor == other.node
        ]

    def get_successors(self):
        return [GraphableCFANode(edge.successor) for edge in self.node.leaving_edges]
    
    def get_node_id(self):
        return self.node.node_id

    def __eq__(self, other):
        return self.node == other.node

    def __hash__(self):
        return self.node.__hash__()
