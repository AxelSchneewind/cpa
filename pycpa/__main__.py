#!/usr/bin/env python

import sys

from pycpa.analyses import ARGCPA
from pycpa.analyses import ARGState

from pycpa.analyses import GraphableARGState
from pycpa.analyses import CompositeCPA
from pycpa.analyses import LocationCPA
from pycpa.analyses import PropertyCPA
from pycpa.analyses import ValueAnalysisCPA

from pycpa import configs

from pycpa.ast import *
from pycpa.cfa import *

from pycpa.cpa import *
from pycpa.cpaalgorithm import *
from pycpa.mcalgorithm import *



import ast
import astpretty
import astunparse

import graphviz
from graphviz import Digraph

import os

def main(args): 
    ast_program = ""

    for program in args.program:
        with open(program) as file:
            ast_program = file.read()

        output_dir = './out/' + program + '/'
        if not os.path.exists(output_dir):
            os.makedirs(output_dir)

        with open(output_dir + '/program.py', 'w') as out_prog:
            out_prog.write(ast_program)

        tree = ast.parse(ast_program)

        # prettyprint ast
        with open(output_dir + '/astpretty', 'w') as out_file:
            out_file.write(astpretty.pformat(tree, show_offsets=False))
    
        # print node types (optional)
        ast_file = open(output_dir + '/ast.txt' ,'w')
        astvisitor = ASTPrinter(ast_file)
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
    
        # 
        module = configs.get_config(args.config)
        property_module = configs.get_property(args.property)

        # 
        cpa = ARGCPA(CompositeCPA(module.get_cpas(cfa_root) + property_module.get_cpas()))

        waitlist = set()
        reached = set()
        init = cpa.get_initial_state()
        waitlist.add(init)
        reached.add(init)
        algo = CPAAlgorithm(cpa)
        algo.run(reached, waitlist)
        dot = graphable_to_dot(
                GraphableARGState(init),
                nodeattrs={"style": "filled", "shape": "box", "color": "white"},
            )
        dot.render(output_dir + '/arg')
    

from pycpa.params import parser


if __name__ == '__main__':
    args = parser.parse_args()
    main(args)
