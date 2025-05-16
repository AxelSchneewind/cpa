#!/usr/bin/env python

from pycpa import configs

from pycpa.preprocessor import preprocess_ast
from pycpa.cfa import *
from pycpa.cpa import *
from pycpa.cpaalgorithm import CPAAlgorithm, Status

from pycpa.specification import Specification
from pycpa.verdict import Verdict

from pycpa.task import Task, Result

import ast
import astpretty
import astunparse

import graphviz
from graphviz import Digraph

import os
import sys



def main(args): 
    ast_program = ""

    aborted = False

    for program in args.program:
        if aborted == True:
            break       

        task = Task(program, args.config, args.property, max_iterations=args.max_iterations)
        print('verifying program', program_name, 'using', args.config, 'against', args.property)


        with open(program) as file:
            ast_program = file.read()


        program_name = os.path.splitext(os.path.basename(program))[0]
        output_dir = './out/' + program_name + '/'
        if not os.path.exists(output_dir):
            os.makedirs(output_dir)


        with open(output_dir + '/program.py', 'w') as out_prog:
            out_prog.write(ast_program)


        print('computing AST', end='')
        tree = preprocess_ast(ast.parse(ast_program))
        with open(output_dir + '/program-preprocessed.py', 'w') as out_prog:
            out_prog.write(astunparse.unparse(tree))

        # prettyprint ast
        with open(output_dir + '/astpretty', 'w') as out_file:
            out_file.write(astpretty.pformat(tree, show_offsets=False))


        # visualize AST
        astvisitor = ASTVisualizer()
        astvisitor.visit(tree)
        astvisitor.graph.render(output_dir + '/ast')
    

        print('\rcomputing CFA', end='')
        # For testing CFA generation
        CFANode.index = 0  # reset the CFA node indices to produce identical output on re-execution
        cfa_creator = CFACreator()
        cfa_creator.visit(tree)
        entry_point = cfa_creator.entry_point
        dot = graphable_to_dot([ GraphableCFANode(r) for r in cfa_creator.roots ])
        dot.render(output_dir + '/cfa')

        # setup cpas and properties
        analysis_mods = [ configs.load_cpa(c) for c in args.config ]
        specification_mods = [ configs.load_specification(p) for p in args.property ]
        cpas = []
        for m in analysis_mods:
            cpas.extend(m.get_cpas(entry_point=entry_point, cfa_roots=cfa_creator.roots,output_dir=output_dir))
        for p in specification_mods:
            cpas.extend(p.get_cpas(entry_point=entry_point, cfa_roots=cfa_creator.roots,output_dir=output_dir))
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

        # run algorithm
        try:
            algo.run(reached, waitlist)
        except KeyboardInterrupt as x:
            result.status = Status.ABORTED_BY_USER
            result.witness = str(x)
            aborted = True
        except BaseException as x:
            result.status = Status.ERROR
            result.witness = str(x)
            raise x
        except:
            result.status = Status.ERROR


        # print status
        print(':  %s' % str(result.status))
        # if result.witness:
        #     print('%s' % str(result.witness))

        # output arg
        dot = graphable_to_dot(
                [ GraphableARGState(init) ],
                nodeattrs={"style": "filled", "shape": "box", "color": "white"},
            )
        dot.render(output_dir + '/arg')


        # compute verdict for each property
        v = Verdict.TRUE if result.status == Status.OK else Verdict.UNKNOWN
        result.verdicts = [v for p in specification_mods]
        for i, p in enumerate(specification_mods):
            result.verdicts[i] = p.get_arg_visitor().visit(init).verdict()
            result.verdict &= result.verdicts[i]

            print('%s:  %s' % (str(task.properties[i]), str(result.verdicts[i])))

    
from pycpa.params import parser


if __name__ == '__main__':
    args = parser.parse_args()
    main(args)
