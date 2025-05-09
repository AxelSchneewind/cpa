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

import os

def main(args): 
    ast_program = ""
    with open(args.program) as file:
        ast_program = file.read()

    output_dir = './out'
    if not os.path.exists(output_dir):
        os.makedirs(output_dir)

    with open(output_dir + '/program.py', 'w') as out_prog:
        out_prog.write(ast_program)

    tree = ast.parse(ast_program)

    # if args.print_ast:
    #     astpretty.pprint(tree, show_offsets=False)
    
    # print node types
    astvisitor = ASTPrinter()
    astvisitor.visit(tree)
    
    # For testing AST generation
    astvisitor = ASTVisualizer()
    astvisitor.visit(tree)
    astvisitor.graph.render(output_dir + '/ast')
    
    # For testing CFA generation
    # In[11]:
    CFANode.index = 0  # reset the CFA node indices to produce identical output on re-execution
    visitor = CFACreator()
    visitor.visit(tree)
    cfa_root = visitor.root
    dot = graphable_to_dot(GraphableCFANode(cfa_root))
    dot.render(output_dir + '/cfa')
    
    
    
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
    dot.render(output_dir + '/arg')
    
    
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
    dot.render(output_dir + '/location')
    
    
    
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
    dot.render(output_dir + '/value-analysis')



   
from pycpa.params import parser
import sys

if __name__ == '__main__':
    args = parser.parse_args()
    main(args)
