#!/usr/bin/env python

import ast
from graphviz import Digraph

# ### 1.2 Converting the AST into a CFA
# 
# For verification, we usually want to get the CFA of the program as an input.
# Constructing the CFA from an AST can be elegantly done using a visitor.
# Our strategy is to consider all nodes that affect control flow and
# take those subtrees that do not directly affect the control flow (like assumptions and statements) as edges in our CFA.
# We will call something that is either an assumption or a statement an `Instruction`.
# We also add some static utility methods to create `Instruction`s of both `InstructionType`s
# and negate an assumption in case it is on the `else` branch:

# In[7]:

from typing import List

from enum import Enum


class InstructionType(Enum):
    STATEMENT = 1,
    ASSUMPTION = 2,
    CALL = 3,
    RETURN = 4,
    NONDET = 5,
    EXIT = 5,
    ABORT = 6,
    REACH_ERROR = 7,
    EXTERNAL = 8,
    NOP = 9

builtin_identifiers = {
    'exit'                          : InstructionType.EXIT,
    'abort'                         : InstructionType.ABORT,
    'call'                          : InstructionType.CALL,
    'return'                        : InstructionType.RETURN,
    'nondet'                        : InstructionType.NONDET,
    '__VERIFIER_nondet_char'        : InstructionType.NONDET,
    '__VERIFIER_nondet_short'       : InstructionType.NONDET,
    '__VERIFIER_nondet_int'         : InstructionType.NONDET,
    '__VERIFIER_nondet_uint'        : InstructionType.NONDET,
    '__VERIFIER_nondet_ulong'       : InstructionType.NONDET,
    '__VERIFIER_nondet_long'        : InstructionType.NONDET,
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
        for p in params:
            if not hasattr(self, p):
                setattr(self, p, params[p])
    
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
    def builtin(expression : ast.Call, ret_variable : str = '__ret', **params):
        assert isinstance(expression, ast.Call)
        name = str(expression.func.id)
        assert name in builtin_identifiers
        return Instruction(expression, kind=builtin_identifiers[name])

    @staticmethod
    def reacherror(expression, **params):
        return Instruction(expression, kind=InstructionType.REACH_ERROR)

    @staticmethod
    def ret(expression : ast.Return):
        assert isinstance(expression, ast.Return)
        return Instruction(expression, kind=InstructionType.RETURN)

    @staticmethod
    def call(expression : ast.Call, declaration : ast.FunctionDef, entry_point : ast.AST, argnames : List[ast.arg], ret_variable : str ='__ret', **params):
        assert isinstance(expression, ast.Call)
        assert isinstance(declaration, ast.FunctionDef)
        assert isinstance(entry_point, CFANode)
        assert all((isinstance(p.arg, ast.Name) or isinstance(p.arg, str) for p in declaration.args.args)), declaration.args.args
        assert all((isinstance(p.arg, ast.Name) or isinstance(p.arg, str) for p in argnames)), argnames
        param_names = [ str(p.arg.id) if isinstance(p.arg, ast.Name) else str(p.arg) for p in declaration.args.args ]
        arg_names   = [ str(p.arg.id) if isinstance(p.arg, ast.Name) else str(p.arg) for p in argnames ]
        return Instruction(expression, kind=InstructionType.CALL, location=entry_point, declaration=declaration, param_names=param_names, arg_names=arg_names, **params)

    @staticmethod
    def nop(expression):
        return Instruction(expression, kind=InstructionType.NOP)





# The  CFA then consists of nodes and edges, for which we declare separate classes.
# A `CFANode` has a numeric node id and a list of leaving and entering edges.
# A `CFAEdge` contains an `Instruction` as well as references to its predecessor and successor `CFANode`s:

# In[8]:

import astpretty

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
    def merge(a, b):
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

    def label(self):
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

# #### Task 3: Creating a CFA from an AST using a visitor (10 points)
# 
# The basic idea is to keep a stack of CFANodes (`self.node_stack`)
# where the top-most element always points to the node where we append the subgraph generated for the current node (and its children).
# Upon entering a node, we generally pop that CFANode from the stack since this is where we append new nodes.
# Once we are done with a node we push its leaving edges back to the stack.
# 
# The following implementation has everything needed for simple programs.
# It just lacks implementation for `break` and `continue`, which will be your task to add.
# (The current implementation considers these statements as no-ops. Please fix it.)

# In[9]:


import ast

class CFACreator(ast.NodeVisitor):
    def __init__(self):
        self.global_root = CFANode()
        self.entry_point = self.global_root
        self.roots = [self.global_root]
        self.node_stack = list()
        self.node_stack.append(self.global_root)
        self.continue_stack = list()
        self.break_stack = list()
        self.function_def = {}
        self.function_entry_point = {}

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

            call = node.value
            self._handle_Call(call, node.targets[0].id)
        else:
            entry_node = self.node_stack.pop()
            exit_node = CFANode()
            edge = CFAEdge(entry_node, exit_node, Instruction.statement(node))
            self.node_stack.append(exit_node)

    def visit_Return(self, node : ast.Return):
        val = node.value if node.value else ast.Constant(0)
        store_instruction = ast.Assign(
                    [ast.Name('__ret', ast.Store())], 
                    val
                )
        store_instruction = ast.copy_location(store_instruction, node)
        ast.fix_missing_locations(store_instruction)
        self.visit(store_instruction)

        entry_node = self.node_stack.pop()
        exit_node = CFANode()
        edge = CFAEdge(entry_node, exit_node, Instruction.ret(node))
        self.node_stack.append(exit_node)

    def _handle_Call(self, call_node : ast.Call, ret_variable : str ='__ret'):
        assert isinstance(call_node, ast.Call), call_node
        assert isinstance(call_node.func, ast.Name), call_node  # function could be attribute (e.g. member functions), not supported

        # make builtin edge
        if call_node.func.id in builtin_identifiers:
            entry_node = self.node_stack.pop()
            exit_node = CFANode()
            edge = CFAEdge(entry_node, exit_node, Instruction.builtin(call_node, ret_variable=ret_variable))
            self.node_stack.append(exit_node)
            return

        if call_node.func.id not in self.function_def or call_node.func.id not in self.function_entry_point:
            print('Warning: call to undefined', ast.unparse(call_node.func))
            return

        # add computing edge for each argument
        arg_names = []
        for i, val in enumerate(call_node.args):
            if isinstance(val, ast.Name):
                argname = str(val.id)
            elif isinstance(val, ast.Constant):
                argname = str(val.value)
            else:
                assert False, 'encountered argument that isnt name or constant'

            arg_names.append(ast.arg(argname))

        pre_jump_node = self.node_stack.pop()
        body_node = CFANode()

        instruction = Instruction.call(call_node, self.function_def[call_node.func.id], self.function_entry_point[call_node.func.id], arg_names, ret_variable=ret_variable)
        edge = CFAEdge(pre_jump_node, body_node, instruction)
        self.node_stack.append(body_node)

    def visit_Call(self, node : ast.Call):
        return self._handle_Call(node)

    def visit_Assert(self, node : ast.Assert):
        raise NotImplementedError('TODO: convert to __VERIFIER_assert in preprocessing')

    def visit_Raise(self, node : ast.Raise):
        # make reacherror edge, i.e. exceptions are used like reacherror()
        entry_node = self.node_stack.pop()
        exit_node = CFANode()
        edge = CFAEdge(entry_node, exit_node, Instruction.reacherror(node))
        self.node_stack.append(exit_node)


# You can use the code below to draw the generated CFAs for manual inspection.
# Essentially, a `CFANode` is wrapped into `GraphableCFANode`, which implements the `Graphable` interface.
# The method `graphable_to_dot` then takes a `Graphable` state and plots everything that is reachable from that state.

# In[10]:


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