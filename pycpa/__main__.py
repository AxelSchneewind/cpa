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

import os
import sys


class LogPrinter:
    def __init__(self, args):
        self.compact = args.compact

    def log_status(self, *msg):
        if not self.compact:
            print('\r',  *msg, end='')

    def log_task(self, programname, configs, properties):
        if not self.compact:
            prop = str(properties[0]) if len(properties) == 1 else properties
            conf = str(configs[0]) if len(configs) == 1 else configs
            print('Verifying ', programname, 'against', prop, 'using', conf)

    def log_result(self, programname, *msg):
        if not self.compact:
            print('\n', programname, ':', *msg)
        else:
            print(programname, ':', *msg)



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
        printer.log_task(program_name, args.config, args.property)

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

        result = Result()

        printer.log_status('running CPA algorithm')
        algo = None

        # root of ARG
        arg = None

        
        specification_mods = [ configs.load_specification(p) for p in args.property ]

        cpas = []
        for p in specification_mods:
            print(p)
            cpas.extend(p.get_cpas(entry_point=entry_point, cfa_roots=cfa_creator.roots,output_dir=output_dir))

        analysis_mods = [ configs.load_cpa(c) for c in args.config ]

        # TODO: clean up this mess, find appropriate abstraction that allows for normal CPA and CEGAR
        init = None
        try:
            if hasattr(analysis_mods[0], 'get_algorithm'):
                algo = analysis_mods[0].get_algorithm(cfa_creator.entry_point, cfa_creator.roots, specification_mods, task, result, printer)

                algo.run_cegar(specification_mods)
                init = algo.get_arg_root()
            else:
                # setup cpas and properties
                for m in analysis_mods:
                    cpas.extend(m.get_cpas(entry_point, cfa_roots=cfa_creator.roots,output_dir=output_dir))
                cpa = ARGCPA(CompositeCPA(cpas))
                init = cpa.get_initial_state()

                # run algorithm
                algo = CPAAlgorithm(cpa, specification_mods, task, result)
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
            if init:
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
