#!/usr/bin/env python

# coding: utf-8

# # Programming Assignment 1: Implementing Configurable Program Analysis
# 
# ## Instructions for Submission and Grading
# 
# - Deadline: **2025-04-08**
# - Total points: 100
#   - There are 10 tasks with 80 points in this Jupyter notebook
#   - We will use 4 hidden programs to test your verifier (20 points, 5 points each)
# - Submission: Upload your finished Jupyter notebook file (i.e., this file) to NTU COOL.
# 
# ## Description
# 
# This programming assignment asks you to implement a minimal software verifier
# based on *Configurable Program Analysis*, the core concept in our course.
# You will practice and apply the concept of CPA by getting your hands dirty.
# 
# The verifier we are going to implement can analyze Python code with basic constructs.
# We leave out the language features unnecessary for grasping the concepts by limiting our verifier to:
# 
# * only integers and Booleans like `True` and `False`
# * only the following operators in expressions: `+ - * / == !=`
# * only `while` loops, `break`, and `continue`, but no for-each loops
# * only assignments of the simple form `a = b + c` (no augmented assignments like ` a += b` or multiple assignments like `(a,b,c) = (1,2,3)`)
# * not consider function declarations. Functions are only used to
#     1. mark target states (by calling `reach_error()`)  
#     2. generate nondeterministic values (by calling `nondet()`)  
#     (These functions can be assumed already-declared, i.e., no need to be declared.)
# 
# Please follow the explanations below to implement the verifier step by step by filling in the TODOs.
# You can test your implementation with the provided programs.

# ## 1. Parsing an input program and generating a CFA (3 tasks, 20 points)
# 
# In this part, we will look at how we can get a CFA from an abstract syntax tree (AST),
# which we will use the Python package `ast` to produce from a given Python program.
# 
# ### 1.1 Visualizing the AST
# 
# A frequently used design pattern to extract information from an AST is the [*visitor pattern*](https://refactoring.guru/design-patterns/visitor).
# In this exercise, we will use it to visualize the AST.
# In later tasks, we will use it for all kinds of other things, like generating the CFA, evaluating expressions, etc.
# We will use the following example program that contains most of the considered syntactical features:

# In order to parse this program into an AST, we use the package `ast` :

# In[2]:


import ast


# This textual representation shows how the AST decomposes the source code into syntactical building blocks.
# More details can be found at https://docs.python.org/3/library/ast.html.
# Basically, every element from the grammar has a corresponding class used in the AST, which is also used for the visitor pattern.
# 
# There is a predefined class `ast.NodeVisitor` from which we can inherit.
# This class contains a method `generic_visit(self, node)` that is called for every node while traversing the AST.
# Below is a simple example of a class `ASTPrinter(ast.NodeVisitor)` that visits each node and
# prints the node's class as well as a number identifying in which order the nodes are explored.
# 
# Furthermore, `ast.NodeVisitor` contains a method `visit_<classname>(self,node)` for every class name that can appear in the AST.
# The default implementation of `generic_visit(self, node)` makes sure that
# this method is called once a corresponding node is encountered in the AST during traversal.
# In the example below, we overwrote one of those methods to show you how this feature can be used.
# Please notice that we still need to call `generic_visit`,
# otherwise the traversal of the AST will stop and child nodes will not be visited.

# In[3]:

import sys

class ASTPrinter(ast.NodeVisitor):
    def __init__(self, file=sys.stdout):
        self.file = file
        self.node_counter = 0

    def generic_visit(self, node):
        node_name = "%d %s" % (self.node_counter, node.__class__.__name__)
        self.node_counter += 1
        self.file.write(node_name + '\n')
        return ast.NodeVisitor.generic_visit(self, node)
    def visit_Assign(self, node):
        self.file.write("Found an assign node:\n")
        self.generic_visit(node)



# #### Task 1: Visitor that counts `Name` nodes (3 points)
# 
# Write a visitor that counts the number of `Name` nodes in an AST:

# In[4]:


class ASTNameCounter(ast.NodeVisitor):
    def __init__(self):
        self.count = 0
    
    def visit_Name(self, node):
        self.count += 1
        return ast.NodeVisitor.generic_visit(self, node)

from graphviz import Digraph

class ASTVisualizer(ast.NodeVisitor):
    def __init__(self):
        self.node_stack = list()
        self.graph = Digraph()
        self.node_counter = 0

    def generic_visit(self, node):
        # using this name in the displayed AST
        node_name = "%d %s" % (self.node_counter, node.__class__.__name__)
        self.node_counter += 1
        self.graph.node(node_name)

        # get parent node's name from stack and create an edge
        if len(self.node_stack) > 0:
            self.graph.edge(self.node_stack[-1], node_name)
            self.node_stack.pop()

        # for each child, push this node's name on the stack
        for c in ast.iter_child_nodes(node):
            self.node_stack.append(node_name)

        return ast.NodeVisitor.generic_visit(self, node)
