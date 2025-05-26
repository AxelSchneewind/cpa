#!/usr/bin/env python

from pycpa import configs

from pycpa.preprocessor import preprocess_ast
from pycpa.cfa import *
from pycpa.cpa import *
from pycpa.cpaalgorithm import CPAAlgorithm, Status

from pycpa.analyses import ARGCPA, CompositeCPA, GraphableARGState

from pycpa.specification import Specification
from pycpa.verdict import Verdict

from pycpa.task import Task, Result

from pycpa.ast import ASTVisualizer

from pycpa.utils.visual import cfa_to_dot, arg_to_dot

import ast
import astpretty

import graphviz
from graphviz import Digraph

import copy

import os
import sys


class LogPrinter:
    def __init__(self, args):
        self.print_status = not args.compact
        self.print_task   = not args.compact

    def log_status(self, *msg):
        if self.print_status:
            print('\r',  *msg, end='')

    def log_task(self, *msg):
        if self.print_task:
            print(*msg)

    def log_result(self, *msg):
        if self.print_status: 
            print('\n', *msg)
        else:
            print(*msg)



def check_arg(arg, task, result, specification_mods):
    ''' compute verdict for each property: traverse the ARG '''
    result.verdicts = [result.verdict for p in specification_mods]
    waitlist = set()
    reached  = set()
    waitlist.add(arg)
    while len(waitlist) > 0:
        state = waitlist.pop()
        reached.add(state)

        for s in state.get_successors():
            if s not in reached:
                waitlist.add(s)

        for i, p in enumerate(specification_mods):
            result.verdicts[i] &= p.check_arg_state(state)
            result.verdict &= result.verdicts[i]


def main(args): 
    ast_program = ""

    aborted = False

    printer = LogPrinter(args)

    for program in args.program:
        if aborted == True:
            break       

        program_name = os.path.splitext(os.path.basename(program))[0]
        task = Task(program, args.config, args.property, max_iterations=args.max_iterations)
        printer.log_task('verifying program', program_name, 'using', args.config, 'against', args.property)

        with open(program) as file:
            ast_program = file.read()


        output_dir = args.output_directory + '/' + program_name + '/'
        if not os.path.exists(output_dir):
            os.makedirs(output_dir)


        with open(output_dir + '/program.py', 'w') as out_prog:
            out_prog.write(ast_program)


        printer.log_status('parsing')
        try:
            tree = ast.parse(ast_program)
        except:
            printer.log_result(program_name, ': invalid')
            continue
        printer.log_status('preprocessing')
        tree = preprocess_ast(tree)
        with open(output_dir + '/program-preprocessed.py', 'w') as out_prog:
            out_prog.write(ast.unparse(tree))

        # prettyprint ast
        with open(output_dir + '/astpretty', 'w') as out_file:
            out_file.write(astpretty.pformat(tree, show_offsets=False))


        # visualize AST
        astvisitor = ASTVisualizer()
        astvisitor.visit(tree)
        astvisitor.graph.render(output_dir + '/ast')
    

        printer.log_status('computing CFA')
        # For testing CFA generation
        CFANode.index = 0  # reset the CFA node indices to produce identical output on re-execution
        cfa_creator = CFACreator()
        cfa_creator.visit(tree)
        entry_point = cfa_creator.entry_point
        dot = cfa_to_dot([ GraphableCFANode(r) for r in cfa_creator.roots ])
        dot.render(output_dir + '/cfa')

        # setup cpas and properties
        analysis_mods = [ configs.load_cpa(c) for c in args.config ]
        specification_mods = [ configs.load_specification(p) for p in args.property ]
        cpas = []
        for m in analysis_mods:
            cpas.extend(m.get_cpas(entry_point=entry_point, cfa_roots=cfa_creator.roots,output_dir=output_dir))
        for p in specification_mods:
            cpas.extend(p.get_cpas(entry_point=entry_point, cfa_roots=cfa_creator.roots,output_dir=output_dir))
        cpa = ARGCPA(CompositeCPA(cpas))

        result = Result()

        printer.log_status('running CPA algorithm')
        init = cpa.get_initial_state()
        algo = None

        if hasattr(analysis_mods[0], 'get_algorithm'):
            algo = analysis_mods[0].get_algorithm(cpa, specification_mods, task, result)
        else:
            algo = CPAAlgorithm(cpa, specification_mods, task, result)

        # root of ARG
        arg = None

        # 
        use_cegar = any('CEGAR' in m.__name__ for m in analysis_mods)

        # run algorithm
        try:
            if use_cegar:
                for k in range(20):
                    init = copy.deepcopy(cpa.get_initial_state())   # make sure to create new arg
                    algo.run(init)

                    cex = algo.make_counterexample(init, algo.result.witness)

                    if cex is not None and not algo.counter_example_feasible(cex):
                        algo.cpa = algo.refine(cpa, cex)
                        if algo.cpa is None: break
                    else:
                        break
            else:
                algo.run(init)
        except KeyboardInterrupt as x:
            result.status = Status.ABORTED_BY_USER
            result.witness = str(x)
            aborted = True
        except BaseException as x:
            result.status = Status.ERROR
            raise x
        except:
            result.status = Status.ERROR
        finally:
            # output arg
            arg = GraphableARGState(init)
            dot = arg_to_dot(
                    [ arg ],
                    nodeattrs={"style": "filled", "shape": "box", "color": "white"},
                )
            dot.render(output_dir + '/arg')

        # print status
        printer.log_status(':  %s' % str(result.status))

        check_arg(arg, task, result, specification_mods)

        printer.log_result(program_name, '%s' % str(result.verdict))

    
from pycpa.params import parser


if __name__ == '__main__':
    args = parser.parse_args()
    main(args)
