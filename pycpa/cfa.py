#!/usr/bin/env python

import ast
from graphviz import Digraph
from typing import List, Optional 

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

from enum import Enum, auto


# class InstructionType(Enum):
#     STATEMENT = 1,
#     ASSUMPTION = 2,
#     CALL = 3,
#     RETURN = 4,
#     NONDET = 5,
#     EXIT = 5,
#     ABORT = 6,
#     REACH_ERROR = 7,
#     EXTERNAL = 8,
#     NOP = 9

class InstructionType(Enum):
    STATEMENT     = auto()
    ASSUMPTION    = auto()
    CALL          = auto()
    RETURN        = auto()
    NONDET        = auto()
    EXIT          = auto()
    ABORT         = auto()
    REACH_ERROR   = auto()
    EXTERNAL      = auto()
    NOP           = auto()

builtin_identifiers = {
    'exit'                          : InstructionType.EXIT,
    'abort'                         : InstructionType.ABORT,
    'call'                          : InstructionType.CALL,
    'return'                        : InstructionType.RETURN,
    'nondet'                        : InstructionType.NONDET,
    "assume"                        : InstructionType.ASSUMPTION,
    "nondet_int"                    : InstructionType.NONDET,
    '__VERIFIER_nondet_char'        : InstructionType.NONDET,
    '__VERIFIER_nondet_short'       : InstructionType.NONDET,
    '__VERIFIER_nondet_int'         : InstructionType.NONDET,
    '__VERIFIER_nondet_uint'        : InstructionType.NONDET,
    '__VERIFIER_nondet_ulong'       : InstructionType.NONDET,
    '__VERIFIER_nondet_long'        : InstructionType.NONDET,
    'reach_error'                   : InstructionType.REACH_ERROR,
}

builtin_identifiers["reach_error"] = InstructionType.REACH_ERROR

class Instruction:
    """An instruction is either an assignment or an assumption"""

    def __init__(self, expression, kind=InstructionType.STATEMENT, **params):
        self.kind = kind
        self.expression = expression
        for p in params:
            if not hasattr(self, p):
                setattr(self, p, params[p])

        match self.kind:
            case InstructionType.CALL:
                assert hasattr(self,'location')
                assert hasattr(self,'declaration')
    
    # def __str__(self):
    #     identifier = str(self.kind).replace('InstructionType.', '')
    #     match self.kind:
    #         case InstructionType.EXIT:
    #             code = self.exit_code if 'exit_code' in self.parameters else '0'
    #             return '%s(%s)' % (identifier, code)
    #         case InstructionType.CALL:
    #             return 'jump %s' % (self.location)
    #         case _:
    #             return '%s' % self.identifier

    def __str__(self):
        """
        Human-readable version of the instruction that never crashes.
        Uses `ast.unparse` (built-in since Python 3.9) for nice code
        snippets; falls back to `ast.dump` if unparse is unavailable.
        """
        try:
            from ast import unparse as _unparse
            _show = lambda e: _unparse(e).strip()
        except ImportError:                       # < 3.9
            _show = lambda e: ast.dump(e)

        match self.kind:
            case InstructionType.ASSUMPTION:
                return f"assume({_show(self.expression)})"
            case InstructionType.STATEMENT:
                return _show(self.expression)
            case InstructionType.CALL:
                return f"call {getattr(self, 'location', '?')}"
            case InstructionType.EXIT:
                code = getattr(self, 'exit_code', 0)
                return f"exit({code})"
            case _:
                return self.kind.name.lower()



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
    def builtin(expression, **params):
        name = str(expression.func.id).strip()
        if name in builtin_identifiers: 
            return Instruction(expression, kind=builtin_identifiers[name])
        else:
            return Instruction(expression, kind=InstructionType.EXTERNAL, **params)

    @staticmethod
    def ret(expression : ast.Return):
        return Instruction(expression, kind=InstructionType.RETURN)

    # @staticmethod
    # def call(expression: ast.Call, declaration: ast.FunctionDef, entry_point, exit_point=None, argnames: List[ast.arg] = None):
    #     assert all((isinstance(p.arg, ast.Name) or isinstance(p.arg, str) for p in declaration.args.args)), declaration.args.args
    #     assert all((isinstance(p.arg, ast.Name) or isinstance(p.arg, str) for p in argnames)), argnames
    #     argnames = argnames or []
    #     assert all((isinstance(p.arg, ast.Name) or isinstance(p.arg, str) for p in argnames)), argnames
    #     param_names = [ str(p.arg.id) if isinstance(p.arg, ast.Name) else str(p.arg) for p in declaration.args.args ]
    #     # TODO
    #     arg_names   = [ str(p.arg.id) if isinstance(p.arg, ast.Name) else str(p.arg) for p in argnames ]

    #     return Instruction(
    #         expression,
    #         kind          = InstructionType.CALL,
    #         location      = entry_point,   # entry of the callee
    #         exit_point    = exit_point,    # (optional) exit of the callee
    #         declaration   = declaration,
    #         param_names   = param_names,
    #         arg_names     = arg_names
    #     )
        # arg_names   = [ str(p.arg.id) if isinstance(p.arg, ast.Name) else str(p.arg) for p in argnames ]
        # return Instruction(expression, kind=InstructionType.CALL, location=entry_point, declaration=declaration, param_names=param_names, arg_names=arg_names)


    @staticmethod
    def call(expression: ast.Call, declaration: ast.FunctionDef, entry_point, exit_point_or_args: Optional[object] = None, argnames: Optional[List[ast.arg]] = None):
        """
        Build a CALL instruction.

        Supports both old and new call sites:

            • Instruction.call(node, decl, entry, args)          # old
            • Instruction.call(node, decl, entry, exit, args)    # new
        """
        # ------------------------------------------------------------------
        # 1.  Disambiguate the positional 4th argument
        # ------------------------------------------------------------------
        from pycpa.cfa import CFANode        # local import to avoid cycles

        if isinstance(exit_point_or_args, CFANode):
            exit_point = exit_point_or_args          # new style
        else:
            # old style: the 4th positional arg was the arg list
            exit_point = None
            if argnames is None:
                argnames = exit_point_or_args

        argnames = argnames or []

        # ------------------------------------------------------------------
        # 2.  Sanity checks and name extraction
        # ------------------------------------------------------------------
        def _to_str(x):
            """Return identifier string for ast.arg, ast.Name or str."""
            if isinstance(x, ast.arg):   # function parameters
                return str(x.arg)
            if isinstance(x, ast.Name):  # plain identifier expr
                return str(x.id)
            return str(x)  
                      # fallback (e.g. already a str)
        # every element must be a supported node
        assert all(isinstance(p, (ast.arg, ast.Name, str))
                for p in declaration.args.args), declaration.args.args
        assert all(isinstance(p, (ast.arg, ast.Name, str))
                for p in argnames), argnames

        param_names = [_to_str(p) for p in declaration.args.args]
        arg_names   = [_to_str(p) for p in argnames]

        # ------------------------------------------------------------------
        # 3.  Create and return the Instruction
        # ------------------------------------------------------------------
        return Instruction(
            expression,
            kind        = InstructionType.CALL,
            location    = entry_point,      # entry node of callee
            exit_point  = exit_point,       # may be None
            declaration = declaration,
            param_names = param_names,
            arg_names   = arg_names
        )

    @staticmethod
    def nop(expression):
        return Instruction(expression, kind=InstructionType.NOP)





# The  CFA then consists of nodes and edges, for which we declare separate classes.
# A `CFANode` has a numeric node id and a list of leaving and entering edges.
# A `CFAEdge` contains an `Instruction` as well as references to its predecessor and successor `CFANode`s:

# In[8]:

import astunparse
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
            return str(self.instruction.expression.lineno) + ': [' + astunparse.unparse(self.instruction.expression).strip() + ']'
        elif self.instruction.kind == InstructionType.STATEMENT:
            return str(self.instruction.expression.lineno) + ': ' + astunparse.unparse(self.instruction.expression).strip()
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

# TODO: somehow track scopes and make variable names fully qualified
# TODO: function for creating temporary variables
class CFACreator(ast.NodeVisitor):
    """
    Builds a control-flow automaton (CFA) from a Python AST.
    After visiting the whole AST you can query:
        • self.roots          – list[CFANode]  (one per function; 0th is global)
        • self.entry_point    – CFANode        (first node of main module)
    """
    def __init__(self) -> None:
        super().__init__()
        self.global_root           = CFANode()        #  entry of the main module
        self.entry_point           = self.global_root
        self.roots:      list[CFANode] = [self.global_root]

        # node-stacks for building edges
        self.node_stack:     list[CFANode] = [self.global_root]
        self.continue_stack: list[CFANode] = []
        self.break_stack:    list[CFANode] = []

        # for (optional) function-call support
        self.function_def:          dict[str, ast.FunctionDef] = {}
        self.function_entry_point:  dict[str, CFANode]         = {}
        self.function_exit_point:   dict[str, CFANode]         = {}

    def generic_visit(self, node):
        super().generic_visit(node)
    
    def visit_Module(self, node: ast.Module):
        for stmt in node.body:
            self.visit(stmt)

    # def visit_FunctionDef(self, node):
    #     pre = self.node_stack.pop()

    #     # for continuing after definition 
    #     post = CFANode()
    #     edge = CFAEdge(pre, post, Instruction.nop(node))
    #     self.node_stack.append(post)

    #     # ignore definitions of builtin functions
    #     if node.name in builtin_identifiers:
    #         return

    #     # 
    #     root = CFANode()
    #     self.function_def[node.name] = node
    #     self.function_entry_point[node.name] = root

    #     self.node_stack.append(root)
    #     self.roots.append(root)
    #     ast.NodeVisitor.generic_visit(self, node)

    def visit_FunctionDef(self, node: ast.FunctionDef):
        entry = CFANode()
        exit_  = CFANode()
        caller = self.node_stack[-1]
        CFAEdge(caller, entry, Instruction.nop(node))   # jump over definition

        self.function_def[node.name]          = node
        self.function_entry_point[node.name]  = entry
        self.function_exit_point[node.name]   = exit_

        self.roots.append(entry)              # so we plot each function

        # visit function body
        self.node_stack.append(entry)
        for stmt in node.body:
            self.visit(stmt)
        body_exit = self.node_stack.pop()
        CFAEdge(body_exit, exit_, Instruction.nop(node))

        # continue in caller
        self.node_stack.append(exit_)

    def visit_While(self, node: ast.While):
        loop_head = self.node_stack.pop()

        # body entry
        body_entry = CFANode()
        CFAEdge(loop_head, body_entry, Instruction.assumption(node.test))

        # exit
        loop_exit = CFANode()
        CFAEdge(loop_head, loop_exit,
                Instruction.assumption(node.test, negated=True))

        # manage break/continue stacks
        self.break_stack.append(loop_exit)
        self.continue_stack.append(loop_head)

        # traverse loop body
        self.node_stack.append(body_entry)
        for stmt in node.body:
            self.visit(stmt)
        body_exit = self.node_stack.pop()
        CFANode.merge(loop_head, body_exit)       # back-edge

        # clean up stacks
        self.break_stack.pop()
        self.continue_stack.pop()

        self.node_stack.append(loop_exit)

    def visit_Break(self, node: ast.Break):
        pred = self.node_stack.pop()
        CFAEdge(pred, self.break_stack[-1], Instruction.statement(node))
        self.node_stack.append(CFANode())         # dead node (no successors)

    def visit_Continue(self, node: ast.Continue):
        pred = self.node_stack.pop()
        CFAEdge(pred, self.continue_stack[-1], Instruction.statement(node))
        self.node_stack.append(CFANode())

    def visit_If(self, node: ast.If):
        entry = self.node_stack.pop()

        # true branch
        true_node = CFANode()
        CFAEdge(entry, true_node, Instruction.assumption(node.test))
        self.node_stack.append(true_node)
        for stmt in node.body:
            self.visit(stmt)
        true_exit = self.node_stack.pop()

        # false branch
        false_node = CFANode()
        CFAEdge(entry, false_node,
                Instruction.assumption(node.test, negated=True))
        self.node_stack.append(false_node)
        for stmt in node.orelse:
            self.visit(stmt)
        false_exit = self.node_stack.pop()

        # merge
        merged = CFANode.merge(true_exit, false_exit)
        self.node_stack.append(merged)

    def visit_Expr(self, node: ast.Expr):
        self.visit(node.value)

    def visit_Assign(self, node: ast.Assign):
        pred = self.node_stack.pop()
        succ = CFANode()
        CFAEdge(pred, succ, Instruction.statement(node))
        self.node_stack.append(succ)

    def visit_Return(self, node: ast.Return):
        pred = self.node_stack.pop()
        succ = CFANode()
        CFAEdge(pred, succ, Instruction.ret(node))
        self.node_stack.append(succ)
        # self.node_stack.append(exit_node)

    # def visit_Call(self, node):
    #     func = node.func.id if isinstance(node.func, ast.Name) else None
    #     if func in self.function_entry_point:
    #         caller = self.node_stack[-1]
    #         entry  = self.function_entry_point[func]
    #         exit_  = self.function_exit_point[func]
    #         declaration = self.function_def[func]              # <— the AST
    #         # get the parameter names for this call
    #         arg_names = [arg.arg for arg in declaration.args.args]

    #         middle = CFANode()
    #         CFAEdge(caller, middle,
    #                 Instruction.call(node, declaration, entry, exit_, arg_names))
    #         # step into function body
    #         self.node_stack.append(middle)
    #         # return from call
    #         CFAEdge(self.node_stack.pop(), exit_, Instruction.nop(node))
    #         self.node_stack.append(exit_)
    #     else:
    #         # still warn on truly undefined calls
    #         print(f"WARNING: call to undefined  {func}")
    def visit_Call(self, node: ast.Call):
        func = node.func.id if isinstance(node.func, ast.Name) else None
        if isinstance(node.func, ast.Name) and node.func.id == "reach_error":
            pred = self.node_stack.pop()
            succ = CFANode()
            CFAEdge(pred, succ, Instruction.builtin(node))   # kind = REACH_ERROR
            self.node_stack.append(succ)
            return

        if func in self.function_entry_point:
            caller = self.node_stack[-1]
            entry = self.function_entry_point[func]
            exit_ = self.function_exit_point[func]
            declaration = self.function_def[func]
            arg_names = [arg.arg for arg in declaration.args.args]

            middle = CFANode()
            CFAEdge(caller, middle,
                    Instruction.call(node, declaration, entry, exit_, arg_names))
            self.node_stack.append(middle)
            CFAEdge(self.node_stack.pop(), exit_, Instruction.nop(node))
            self.node_stack.append(exit_)
        else:
            print(f"WARNING: call to undefined {func}")


        if node.func.id in self.function_def and node.func.id not in builtin_identifiers:
            # add computing edge for each argument
            arg_names = []
            for i, val in enumerate(node.args):
                if isinstance(val, ast.Name):
                    argname = str(val.id)
                elif isinstance(val, ast.Constant):
                    argname = str(val.value)
                else:
                    argname = '__' + str(i)
                    arg_expr = ast.Expr(
                                    ast.Assign(
                                        [ast.Name(argname, ast.Store())], val, 
                                    ),
                                )
                    arg_expr = ast.copy_location(arg_expr, node)
                    arg_expr = ast.fix_missing_locations(arg_expr)
                    self.visit(arg_expr)

                arg_names.append(ast.arg(argname))
            
            # inlining:
            # pre_jump_node = self.node_stack.pop()
            # body_node = CFANode()
            # edge = CFAEdge(pre_jump_node, body_node, Instruction.statement(node))
            # self.node_stack.append(body_node)

            # for b in self.function_def[node.func.id].body:
            #     self.visit(b)
            pre_jump_node = self.node_stack.pop()
            body_node = CFANode()
            edge = CFAEdge(pre_jump_node, body_node, Instruction.call(node, self.function_def[node.func.id], self.function_entry_point[node.func.id], arg_names))
            self.node_stack.append(body_node)
            return

        print('WARNING: call to undefined ', node.func.id, '')

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

    def __eq__(self, other):
        return self.node == other.node

    def __hash__(self):
        return self.node.__hash__()

def graphable_to_dot(roots, nodeattrs={"shape": "circle"}):
    assert isinstance(roots, list)
    dot = Digraph()
    for (key, value) in nodeattrs.items():
        dot.attr("node", [(key, value)])
    for root in roots:
        dot.node(root.get_node_label())
        waitlist = set()
        waitlist.add(root)
        reached = set()
        reached.add(root)
        while not len(waitlist) == 0:
            node = waitlist.pop()
            for successor in node.get_successors():
                for edgelabel in node.get_edge_labels(successor):
                    dot.edge(node.get_node_label(), successor.get_node_label(), edgelabel)
                if not successor in reached:
                    waitlist.add(successor)
                    reached.add(successor)
                    dot.node(successor.get_node_label())
    return dot

