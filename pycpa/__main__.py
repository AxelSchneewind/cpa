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

from pycpa.verdict import Verdict, evaluate_arg_safety

from pycpa.task import Task, Result

import ast
import astpretty
import astunparse

import graphviz
from graphviz import Digraph

import os


def main(args): 
    ast_program = ""

    for program in args.program:
        task = Task(program, args.config, args.property, max_iterations=args.max_iterations)

        with open(program) as file:
            ast_program = file.read()

        program_name = os.path.splitext(os.path.basename(program))[0]
        output_dir = './out/' + program_name + '/'
        if not os.path.exists(output_dir):
            os.makedirs(output_dir)

        print('verifying program', program_name, 'using', args.config, 'against', args.property)
        with open(output_dir + '/program.py', 'w') as out_prog:
            out_prog.write(ast_program)

        print('computing AST', end='')
        tree = ast.parse(ast_program)

        # prettyprint ast
        with open(output_dir + '/astpretty', 'w') as out_file:
            out_file.write(astpretty.pformat(tree, show_offsets=False))


        # print node types (optional)
        ast_file = open(output_dir + '/ast.txt' ,'w')
        astvisitor = ASTPrinter(ast_file)
        astvisitor.visit(tree)
    
        # visualize AST
        astvisitor = ASTVisualizer()
        astvisitor.visit(tree)
        astvisitor.graph.render(output_dir + '/ast')
    

        print('\rcomputing CFA', end='')
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
        modules = [ configs.get_config(c) for c in args.config ]
        property_modules = [ configs.get_property(p) for p in args.property ]
        cpas = []
        for m in modules:
            cpas.extend(m.get_cpas(cfa_root))
            
        for p in property_modules:
            cpas.extend(p.get_cpas())

        # 
        cpa = ARGCPA(CompositeCPA(cpas))


        result = Result()

        print('\rrunning CPA algorithm', end='')
        waitlist = set()
        reached = set()
        init = cpa.get_initial_state()
        waitlist.add(init)
        reached.add(init)
        algo = CPAAlgorithm(cpa, task, result)
        algo.run(reached, waitlist)

        # print status
        print(':  %s' % str(result.status))

        # output arg
        dot = graphable_to_dot(
                GraphableARGState(init),
                nodeattrs={"style": "filled", "shape": "box", "color": "white"},
            )
        dot.render(output_dir + '/arg')


        # compute verdict for each property
        v = result.verdict
        result.verdicts = [result.verdict for p in property_modules]
        for i,p in enumerate(property_modules):
            result.verdicts[i] = evaluate_arg_safety(init, p.state_property)
            result.verdict &= v

            print('%s:  %s' % (str(task.properties[i]), str(result.verdict)))

    
from pycpa.params import parser


if __name__ == '__main__':
    args = parser.parse_args()
    main(args)
