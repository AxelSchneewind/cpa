#!/usr/bin/env python

from pycpa import configs

from pycpa.ast import ASTChecker
from pycpa.preprocessor import preprocess_ast
from pycpa.cfa import *
from pycpa.cpa import *
from pycpa.cpaalgorithm import CPAAlgorithm, Status

from pycpa.analyses import ARGCPA, CompositeCPA, GraphableARGState

from pycpa.verdict import Verdict

from pycpa.task import Task, Result

from pycpa.ast import ASTVisualizer

from pycpa.utils.visual import cfa_to_dot, arg_to_dot

from pycpa import log

import ast
import astpretty

import graphviz
from graphviz import Digraph

import os
import sys

import yaml


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
    aborted = False

    log.init_printer(args)

    for program in args.program:
        if aborted == True:
            break       

        # process program argument
        extension = os.path.splitext(os.path.basename(program))[1]
        if extension == '.yml':
            with open(program, 'r') as file:
                task_yml = yaml.safe_load(file)
                task = Task.task_from_yml(task_yml, os.path.dirname(program), args)
        else:
            task = Task.task_from_args(program, os.path.dirname(program), args)

        log.printer.log_task(task.program_name, args.config, args.property)

        # read program file
        with open(task.program) as file:
            ast_program = file.read()


        # prepare output directory
        output_dir = args.output_directory + '/' + task.program_name + '/'
        if not os.path.exists(output_dir):
            os.makedirs(output_dir)

        # write program
        with open(output_dir + '/program.py', 'w') as out_prog:
            out_prog.write(ast_program)

        # parse program into ast
        log.printer.log_status('parsing')
        try:
            tree = ast.parse(ast_program)
        except:
            log.printer.log_result(task.program_name, 'SYNTAX_INVALID', str(Verdict.UNKNOWN))
            continue

        # perform preprocessing on ast
        log.printer.log_status('preprocessing')
        tree = preprocess_ast(tree)
        with open(output_dir + '/program-preprocessed.py', 'w') as out_prog:
            out_prog.write(ast.unparse(tree))
        try:
            ASTChecker().visit(tree)
        except:
            log.printer.log_result(task.program_name, 'SYNTAX_INVALID', str(Verdict.UNKNOWN))
            continue

        # prettyprint ast
        with open(output_dir + '/astpretty', 'w') as out_file:
            out_file.write(astpretty.pformat(tree, show_offsets=False))

        # visualize ast
        astvisitor = ASTVisualizer()
        astvisitor.visit(tree)
        astvisitor.graph.render(output_dir + '/ast')
    

        # compute cfa
        log.printer.log_status('computing CFA')
        CFANode.index = 0  # reset the CFA node indices to produce identical output on re-execution
        cfa_creator = CFACreator()
        cfa_creator.visit(tree)
        entry_point = cfa_creator.entry_point
        dot = cfa_to_dot([ GraphableCFANode(r) for r in cfa_creator.roots ])
        dot.render(output_dir + '/cfa')


        result = Result()

        log.printer.log_status('running CPA algorithm')
        arg = None      # root of ARG

        
        # load specification modules
        specification_mods = [ configs.load_specification(p) for p in args.property ]

        # load cpas for specification
        cpas = []
        for p in specification_mods:
            cpas.extend(p.get_cpas(entry_point=entry_point, cfa_roots=cfa_creator.roots,output_dir=output_dir))

        analysis_mods = [ configs.load_cpa(c) for c in args.config ]

        # TODO: clean up this mess, find appropriate abstraction that allows for normal CPA and CEGAR
        init = None
        try:
            if hasattr(analysis_mods[0], 'get_algorithm'):
                algo = analysis_mods[0].get_algorithm(cfa_creator.entry_point, cfa_creator.roots, specification_mods, task, result)

                algo.run()
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
        # check safety of arg
        check_arg(arg, task, result, specification_mods)

        # print status
        log.printer.log_result(task.program_name, str(result.status), str(result.verdict))


    
from pycpa.params import parser


if __name__ == '__main__':
    args = parser.parse_args()
    main(args)
