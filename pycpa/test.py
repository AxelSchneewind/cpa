#!/usr/bin/env python

from pycpa.analyses import PredAbsPrecision
from pycpa.cfa import CFACreator, InstructionType
from pycpa.preprocessor import preprocess_ast

from pycpa.analyses import PredAbsCPA, PredAbsState, PredAbsTransferRelation, PredAbsPrecision


import ast
import astpretty

import graphviz
from graphviz import Digraph

import os
import sys





def test_precision(program : str):
    tree = ast.parse(program)
    cfa_creator = CFACreator()
    cfa_creator.visit(tree)
    entry_point = cfa_creator.entry_point

    # test formula generation using FormulaBuilder
    precision = PredAbsPrecision.from_cfa([entry_point])
    return precision


def test_formula(line : str, ssa_indices : dict[str,int]):
    # get a single cfa edge from the given line
    tree = ast.parse(line)
    cfa_creator = CFACreator()
    cfa_creator.visit(tree)
    entry_point = cfa_creator.entry_point
    assert len(entry_point.leaving_edges) > 0, tree.body
    edge = entry_point.leaving_edges[0]

    # test formula generation using FormulaBuilder
    match edge.instruction.kind:
        case InstructionType.STATEMENT:
            assert isinstance(edge.instruction.expression, ast.Assign)
            formula = PredAbsPrecision.ssa_from_assign(edge, ssa_indices=ssa_indices)
        case InstructionType.ASSUME:
            formula = PredAbsPrecision.ssa_from_assume(edge, ssa_indices=ssa_indices)
        case _:
            pass
    return formula


def test_transfer_relation(line : str, predecessor : PredAbsState, transfer_relation : PredAbsTransferRelation):
    # get a single cfa edge from the given line
    tree = ast.parse(line)
    cfa_creator = CFACreator()
    cfa_creator.visit(tree)
    entry_point = cfa_creator.entry_point
    assert len(entry_point.leaving_edges) > 0, tree.body
    edge = entry_point.leaving_edges[0]

    # test formula generation using FormulaBuilder
    successors = transfer_relation.get_abstract_successors_for_edge(predecessor, edge)
    print(successors[0])
    return successors[0]



test_program = '''a = 1
b = 2
c = a + b
c = (a == b) or (b == 3) or not (a == 1)
x = 10
y = x + y
z = collatz(z)
b = VERIFIER_assert((x%2 == 0)) '''


if __name__ == '__main__':
    # compute precision from cfa
    print('computing initial precision: ')
    precision = test_precision(test_program)
    print(precision)

    # compute ssa path formula
    print('computing clauses of formula for example program: ')
    ssa_indices = {}
    for line in test_program.split('\n'):
        print(line)
        formula = test_formula(line, ssa_indices)
        print(formula)

    # run cpa
    print('computing CPA state transfers: ')
    cpa = PredAbsCPA(precision)
    state = cpa.get_initial_state()
    transfer = cpa.get_transfer_relation()
    for line in test_program.split('\n'):
        print(line)
        state = test_transfer_relation(line, state, transfer)
        print(formula)





