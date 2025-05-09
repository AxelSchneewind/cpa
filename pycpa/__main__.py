#!/usr/bin/env python

import sys
sys.path.append('.')

from pycpa.analyses import ARGCPA
from pycpa.analyses import ARGState

from pycpa.analyses import GraphableARGState
from pycpa.analyses import CompositeCPA
from pycpa.analyses import LocationCPA
from pycpa.analyses import PropertyCPA
from pycpa.analyses import ValueAnalysisCPA

from pycpa.AST import *
from pycpa.CFA import *

from pycpa.CPA import *
from pycpa.CPAAlgorithm import *
from pycpa.MCAlgorithm import *



import ast
import astpretty
import astunparse

import graphviz
from graphviz import Digraph


def main(args): 
    # Example program for testing
    # In[1]:
    ast_program = \
    """
i = 0
j = nondet()
while i<100:
  if i == 47:
    j = j * 2 - 1
    reach_error()
    break
  else:
    i = i + 1
    continue
  i = i - 1
    """
    
    tree = ast.parse(ast_program)
    astpretty.pprint(tree, show_offsets=False)
    
    # print node types
    astvisitor = ASTPrinter()
    astvisitor.visit(tree)
    
    # In[5]:
    dot = graphviz.Digraph()
    dot.node("node1")
    dot.node("node2")
    dot.edge("node1","node2")
    
    
    # For testing AST generation
    astvisitor = ASTVisualizer()
    astvisitor.visit(tree)
    astvisitor.graph.render('ast')
    
    
    
    # For testing CFA generation
    # In[11]:
    CFANode.index = 0  # reset the CFA node indices to produce identical output on re-execution
    visitor = CFACreator()
    visitor.visit(tree)
    cfa_root = visitor.root
    graphable_to_dot(GraphableCFANode(cfa_root))
    dot.render('cfa')
    
    
    
    # In[18]:
    CFANode.index = 0  # reset the CFA node indices to produce identical output on re-execution
    cfa_creator = CFACreator()
    cfa_creator.visit(tree)
    cfa_root = cfa_creator.root
    
    cpa = ARGCPA(
            LocationCPA(cfa_root)
        )
    
    waitlist = set()
    reached = set()
    init = cpa.get_initial_state()
    waitlist.add(init)
    reached.add(init)
    algo = MCAlgorithm(cpa)
    algo.run(reached, waitlist)
    dot = graphable_to_dot(
            GraphableARGState(init),
            nodeattrs={"style": "filled", "shape": "box", "color": "white"},
        )
    dot.render('arg')
    
    
    # In[21]:
    
    
    simple_program = \
    """
i = 0
j = nondet()
while i==0:
  if not i == 47:
    j = 47
    reach_error()
  else:
    i = 142
  i = j
    """
    simple_program2 = \
    """
i=0
j=0
while i==0:
  j=1
    """
    tree = ast.parse(simple_program)
    tree2 = ast.parse(simple_program2)
    
    CFANode.index = 0  # reset the CFA node indices to produce identical output on reexecution
    cfa_creator = CFACreator()
    cfa_creator.visit(tree)
    graphable_to_dot(GraphableCFANode(cfa_creator.root))
    
    
    # In[22]:
    
    
    ARGState.index = 0
    CFANode.index = 0  # reset the CFA node indices to produce identical output on reexecution
    cfa_creator = CFACreator()
    cfa_creator.visit(tree)
    cfa_root = cfa_creator.root
    
    cpa = ARGCPA(
            LocationCPA(cfa_root)
        )
    
    waitlist = set()
    reached = set()
    init = cpa.get_initial_state()
    waitlist.add(init)
    reached.add(init)
    algo = MCAlgorithm(cpa)
    algo.run(reached, waitlist)
    dot = graphable_to_dot(
            GraphableARGState(init),
            nodeattrs={"style": "filled", "shape": "box", "color": "white"},
        )
    dot.render('location')
    
    
    
    # Let's try to verify `simple_program` using the model-checking algorithm.
    # Note that, you do not need to implement every arithmetic operator to handle this task.
    # Can your value analysis find a bug in `simple_program`?
    
    # In[26]:
    
    
    ARGState.index = 0
    CFANode.index = 0  # reset the CFA node indices to produce identical output on re-execution
    cfa_creator = CFACreator()
    cfa_creator.visit(tree)
    cfa_root = cfa_creator.root
    
    cpa = ARGCPA(CompositeCPA([LocationCPA(cfa_root), ValueAnalysisCPA()]))
    
    waitlist = set()
    reached = set()
    init = cpa.get_initial_state()
    waitlist.add(init)
    reached.add(init)
    algo = MCAlgorithm(cpa)
    algo.run(reached, waitlist)
    dot = graphable_to_dot(
            GraphableARGState(init),
            nodeattrs={"style": "filled", "shape": "box", "color": "white"},
        )
    dot.render('value-analysis')
    
    # Next, let's try to verify `simple_program2`, which contains a while-loop.
    # Can your value analysis terminate on this program?
    
    # In[27]:
    
    
    ARGState.index = 0
    CFANode.index = 0  # reset the CFA node indices to produce identical output on re-execution
    cfa_creator = CFACreator()
    cfa_creator.visit(tree2)
    cfa_root = cfa_creator.root
    
    cpa = ARGCPA(CompositeCPA([LocationCPA(cfa_root), ValueAnalysisCPA()]))
    
    waitlist = set()
    reached = set()
    init = cpa.get_initial_state()
    waitlist.add(init)
    reached.add(init)
    algo = MCAlgorithm(cpa)
    algo.run(reached, waitlist)
    dot = graphable_to_dot(
            GraphableARGState(init),
            nodeattrs={"style": "filled", "shape": "box", "color": "white"},
        )
    dot.render('value-analysis-while')
    



from pycpa.params import parser
import sys

if __name__ == '__main__':
    args = parser.parse_args()
    main(args)
