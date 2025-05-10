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


from enum import Enum
class InstructionType(Enum):
    STATEMENT = 1
    ASSUMPTION = 2
    JUMP = 3


class Instruction:
    """An instruction is either an assignment or an assumption"""

    def __init__(self, expression, kind=InstructionType.STATEMENT, negated=False):
        self.kind = kind
        self.expression = expression
        self.negated = negated  # we might need this information at some point

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
    def jump(location):
        return Instruction(location, kind=InstructionType.JUMP)


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
            return '[' + astunparse.unparse(self.instruction.expression).strip() + ']'
        elif self.instruction.kind == InstructionType.STATEMENT:
            return astunparse.unparse(self.instruction.expression).strip()
        elif self.instruction.kind == InstructionType.JUMP:
            return 'goto %s' % self.instruction.location

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

# TODO: somehow track scopes
class CFACreator(ast.NodeVisitor):
    def __init__(self):
        self.root = CFANode()
        self.node_stack = list()
        self.node_stack.append(self.root)
        self.continue_stack = list()
        self.break_stack = list()
        self.function_def = {}

    def generic_visit(self, node):
        ast.NodeVisitor.generic_visit(self, node)

    def visit_FunctionDef(self, node):
        self.function_def[node.name] = node
        if node.name == 'main':
            ast.NodeVisitor.generic_visit(self, node)

    def visit_While(self, node): # Note: implement TODOs for break and continue to handle them inside while-loops
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

    # DONE Task 3 (add proper implementation for break)
    def visit_Break(self, node):
        entry_node = self.node_stack.pop()
        next_node = CFANode()            # create node for next line after break

        # make edge from entry node to break node
        edge = CFAEdge(
            entry_node, self.break_stack[-1], Instruction.statement(node)
        )

        self.node_stack.append(next_node)
        return 

    # DONE Task 3 (add proper implementation for continue)
    def visit_Continue(self, node):
        entry_node = self.node_stack.pop()
        next_node = CFANode()             # create node for next line after break

        # make edge from entry node to continue node
        edge = CFAEdge(
            entry_node, self.continue_stack[-1], Instruction.statement(node)
        )

        self.node_stack.append(next_node)
        return

    def visit_If(self, node):
        entry_node = self.node_stack.pop()
        left = CFANode()
        edge = CFAEdge(entry_node, left, Instruction.assumption(node.test))
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

    def visit_Expr(self, node):
        # entry_node = self.node_stack.pop()
        # exit_node = CFANode()
        # edge = CFAEdge(entry_node, exit_node, Instruction.statement(node))
        # self.node_stack.append(exit_node)
        self.visit(node.value)

    # TODO: get calls from expression and run these before assignment
    def visit_AugAssign(self, node):
        entry_node = self.node_stack.pop()
        exit_node = CFANode()
        edge = CFAEdge(entry_node, exit_node, Instruction.statement(node))
        self.node_stack.append(exit_node)

    def visit_Assign(self, node):
        entry_node = self.node_stack.pop()
        exit_node = CFANode()
        edge = CFAEdge(entry_node, exit_node, Instruction.statement(node))
        self.node_stack.append(exit_node)

    def visit_Return(self, node):
        val = node.value if node.value else ast.Constant(0, lineno=node.lineno, col_offset=node.col_offset)
        self.visit(
            ast.Expr(
                value=ast.Assign(
                    [ast.Name('__ret', ast.Store(), lineno=node.lineno, col_offset=node.col_offset)], 
                    val,
                    lineno=node.lineno, col_offset=node.col_offset
                ), 
                lineno=node.lineno, col_offset=node.col_offset
            )
        )

    def visit_Call(self, node):
        entry_node = self.node_stack.pop()
        self.node_stack.append(entry_node)

        # inlining:
        if node.func.id in self.function_def:
            for name, val in zip(self.function_def[node.func.id].args.args, node.args):
                self.visit(
                    ast.Expr(
                        ast.Assign(
                            [name], val, 
                            lineno=node.lineno, col_offset=node.col_offset
                        ),
                        lineno=node.lineno, col_offset=node.col_offset
                    )
                )
            
            jump_node = self.node_stack.pop()

            body_node = CFANode()
            edge = CFAEdge(jump_node, body_node, Instruction.statement(node))

            self.node_stack.append(body_node)

            for b in self.function_def[node.func.id].body:
                self.visit(b)

        # TODO: insert storing of return value



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

def graphable_to_dot(root, nodeattrs={"shape": "circle"}):
    dot = Digraph()
    for (key, value) in nodeattrs.items():
        dot.attr("node", [(key, value)])
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

