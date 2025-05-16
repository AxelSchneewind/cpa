#!/usr/bin/env python

from pycpa.cfa import InstructionType
from pycpa.cpa import CPA, AbstractState, TransferRelation, StopSepOperator, MergeSepOperator

from pycpa.analyses.PredAbsPrecision import PredAbsPrecision

from pysmt.shortcuts import TRUE, And, Or
import pysmt

import ast
import copy

import astunparse
import astpretty


class PredAbsState(AbstractState):
    def __init__(self, other=None):
        if other:
            self.formula = copy.copy(other.formula)
            self.ssa_indices = copy.copy(other.ssa_indices)
        else:
            self.formula = TRUE()
            self.ssa_indices = {}

    def subsumes(self, other):
        """
            TODO: check implication i guess (self.formula => other.formula)
            should be doable using pySMT satisfiability check
        """
        return False
    def __eq__(self, other):
        return self.formula == other.formula

    def __hash__(self):
        return self.formula.__hash__()

    def __str__(self):
        return "{%s}" % self.formula


class PredAbsTransferRelation(TransferRelation):
    def __init__(self, precision : set[pysmt.fnode]):
        self.precision = precision

    def get_abstract_successors(self, predecessor):
        raise NotImplementedError(
            "successors without edge not possible for Predicate Analysis!"
        )

    def get_abstract_successors_for_edge(self, predecessor, edge):
        old = predecessor.formula
        match edge.instruction.kind:
            case InstructionType.STATEMENT:
                formula = PredAbsPrecision.ssa_from_assign(edge, predecessor.ssa_indices)
                print('statement edge: ', formula)
                # TODO
                return [copy.copy(predecessor)]
            case InstructionType.ASSUMPTION:
                formula = PredAbsPrecision.ssa_from_assume(edge, predecessor.ssa_indices)
                print('assume edge: ', formula)
                # TODO
                return [copy.copy(predecessor)]
            case InstructionType.CALL | InstructionType.NONDET:
                # ignore this for now
                return [copy.copy(predecessor)]
            case _:
                return [copy.copy(predecessor)]


class PredAbsCPA(CPA):
    def __init__(self, initial_precision : set[pysmt.fnode]):
        self.precision = initial_precision

    def get_initial_state(self):
        return PredAbsState()

    def get_stop_operator(self):
        return StopSepOperator(PredAbsState.subsumes)

    def get_merge_operator(self):
        return MergeSepOperator()

    def get_transfer_relation(self):
        return PredAbsTransferRelation(self.precision)




