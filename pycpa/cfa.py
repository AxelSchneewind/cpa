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

    After visiting an entire module you can read:
        self.entry_point        – CFANode  (first node of main code)
        self.roots              – list[CFANode] (one root per function, plus 0th = global)
    """

    # ------------------------------------------------------------------ #
    # init                                                               #
    # ------------------------------------------------------------------ #
    def __init__(self) -> None:
        super().__init__()

        self.global_root = CFANode()          # first node of top-level code
        self.entry_point = self.global_root   # <-- attribute main() expects
        self.roots: list[CFANode] = [self.global_root]

        # work-stacks
        self.node_stack     : list[CFANode] = [self.global_root]
        self.break_stack    : list[CFANode] = []
        self.continue_stack : list[CFANode] = []

        # function maps
        self.function_def         : dict[str, ast.FunctionDef] = {}
        self.function_entry_point : dict[str, CFANode] = {}
        self.function_exit_point  : dict[str, CFANode] = {}

    # ------------------------------------------------------------------ #
    # generic visitors                                                   #
    # ------------------------------------------------------------------ #
    def visit_Module(self, node: ast.Module):
        for stmt in node.body:
            self.visit(stmt)

    # -------- function definitions ------------------------------------ #
    def visit_FunctionDef(self, node: ast.FunctionDef):
        entry = CFANode(); exit_ = CFANode()
        caller = self.node_stack[-1]          # current basic block
        CFAEdge(caller, entry, Instruction.nop(node))   # skip over def

        self.function_def[node.name]         = node
        self.function_entry_point[node.name] = entry
        self.function_exit_point [node.name] = exit_
        self.roots.append(entry)

        # visit body
        self.node_stack.append(entry)
        for stmt in node.body:
            self.visit(stmt)
        body_exit = self.node_stack.pop()

        CFAEdge(body_exit, exit_, Instruction.nop(node))
        self.node_stack.append(exit_)        # continue after def

    # ------------------------------------------------------------------ #
    # loops                                                              #
    # ------------------------------------------------------------------ #
    def visit_While(self, node: ast.While):
        head = self.node_stack.pop()

        body_entry = CFANode()
        CFAEdge(head, body_entry, Instruction.assumption(node.test))

        loop_exit = CFANode()
        CFAEdge(head, loop_exit,
                Instruction.assumption(node.test, negated=True))

        self.break_stack.append(loop_exit)
        self.continue_stack.append(head)

        self.node_stack.append(body_entry)
        for stmt in node.body:
            self.visit(stmt)
        body_exit = self.node_stack.pop()
        CFANode.merge(head, body_exit)

        self.continue_stack.pop(); self.break_stack.pop()
        self.node_stack.append(loop_exit)

    def visit_Break(self, node: ast.Break):
        pred = self.node_stack.pop()
        CFAEdge(pred, self.break_stack[-1], Instruction.nop(node))
        self.node_stack.append(CFANode())     # dead successor

    def visit_Continue(self, node: ast.Continue):
        pred = self.node_stack.pop()
        CFAEdge(pred, self.continue_stack[-1], Instruction.nop(node))
        self.node_stack.append(CFANode())

    # ------------------------------------------------------------------ #
    # conditionals                                                       #
    # ------------------------------------------------------------------ #
    def visit_If(self, node: ast.If):
        entry = self.node_stack.pop()

        t_entry = CFANode()
        CFAEdge(entry, t_entry, Instruction.assumption(node.test))
        self.node_stack.append(t_entry)
        for s in node.body:
            self.visit(s)
        t_exit = self.node_stack.pop()

        f_entry = CFANode()
        CFAEdge(entry, f_entry,
                Instruction.assumption(node.test, negated=True))
        self.node_stack.append(f_entry)
        for s in node.orelse:
            self.visit(s)
        f_exit = self.node_stack.pop()

        merged = CFANode.merge(t_exit, f_exit)
        self.node_stack.append(merged)

    # ------------------------------------------------------------------ #
    # CALL-handling helper                                               #
    # ------------------------------------------------------------------ #
    def _build_call_edges(self, call: ast.Call, ret_var: str | None):
        # reach_error special-case
        if isinstance(call.func, ast.Name) and call.func.id == "reach_error":
            pred = self.node_stack.pop()
            succ = CFANode()
            succ.is_error = True                 # <-- add this line
            CFAEdge(pred, succ, Instruction.builtin(call))
            self.node_stack.append(succ)
            return

        fname = call.func.id if isinstance(call.func, ast.Name) else None
        if fname not in self.function_entry_point:
            # unknown – external
            pred = self.node_stack.pop(); succ = CFANode()
            CFAEdge(pred, succ, Instruction.builtin(call))
            self.node_stack.append(succ)
            return

        # known function
        entry  = self.function_entry_point[fname]
        exit_  = self.function_exit_point [fname]
        decl   = self.function_def[fname]

        arg_names = [
            n.id if isinstance(n, ast.Name) else f"tmp_const_{i}"
            for i, n in enumerate(call.args)
        ]

        pre  = self.node_stack.pop()
        post = CFANode()

        instr = Instruction.call(call, decl, entry, exit_, arg_names)
        instr.ret_var = ret_var

        CFAEdge(pre,  entry, instr)          # CALL
        CFAEdge(exit_, post, Instruction.nop(call))  # RETURN
        self.node_stack.append(post)

    # ------------------------------------------------------------------ #
    # statements                                                         #
    # ------------------------------------------------------------------ #
    def visit_Assign(self, node: ast.Assign):
        if isinstance(node.value, ast.Call) and isinstance(node.targets[0], ast.Name):
            self._build_call_edges(node.value, ret_var=node.targets[0].id)
        else:
            if not self.node_stack:
                self.node_stack.append(CFANode())
            pred = self.node_stack.pop(); succ = CFANode()
            CFAEdge(pred, succ, Instruction.statement(node))
            self.node_stack.append(succ)

    def visit_Expr(self, node: ast.Expr):
        if isinstance(node.value, ast.Call):
            self._build_call_edges(node.value, ret_var=None)
        else:
            pred = self.node_stack.pop(); succ = CFANode()
            CFAEdge(pred, succ, Instruction.statement(node.value))
            self.node_stack.append(succ)

    def visit_Return(self, node: ast.Return):
        pred = self.node_stack.pop(); succ = CFANode()
        CFAEdge(pred, succ, Instruction.ret(node))
        self.node_stack.append(succ)

    def visit_Assert(self, node: ast.Assert):
        pred = self.node_stack.pop()
        succ = CFANode()
        CFAEdge(pred, succ, Instruction.assumption(node.test))
        # print(f"[DEBUG CFA] assert→assume edge for {ast.dump(node.test)}")
        self.node_stack.append(succ)

    def visit_Raise(self, node: ast.Raise):
        # Pop the current block, create an error‐successor, and mark it.
        pred = self.node_stack.pop()
        succ = CFANode()
        succ.is_error = True

        # Emit a genuine REACH_ERROR–kind edge, not just a statement.
        CFAEdge(pred, succ, Instruction(node, kind=InstructionType.REACH_ERROR))
        # print(f"[DEBUG CFA] raise→error-edge for {ast.dump(node)}")

        # Continue from the “error” node (so other passes see it).
        self.node_stack.append(succ)

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

