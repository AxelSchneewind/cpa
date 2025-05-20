#!/usr/bin/env python

from pycpa.cfa import InstructionType
from pycpa.cpa import CPA, AbstractState, TransferRelation, StopSepOperator, MergeSepOperator

from pycpa.analyses.PredAbsPrecision import PredAbsPrecision

from pysmt.shortcuts import TRUE, And, Or
import pysmt

import ast
import copy

import astpretty


class PredAbsState(AbstractState):
    def __init__(self, other=None):
        if other is not None:
            self.predicates = copy.copy(other.predicates)
            self.ssa_indices = copy.copy(other.ssa_indices)
        else:
            self.predicates  : set[pysmt.fnode] = set()         # set of predicates
            self.ssa_indices : dict[str,int]    = dict()        # mapping from program variable names to their highest ssa index

    def subsumes(self, other):
        return self.predicates.issubset(other.predicates)   # simple subset check

    def __eq__(self, other):
        return isinstance(other, PredAbsState) and self.predicates == other.predicates

    def __hash__(self):
        assert self.predicates is not None, self
        result = len(self.predicates) * len(self.ssa_indices) * id(self.predicates) * id(self.ssa_indices)
        return result

    def __str__(self):
        return "{%s}" % self.predicates


class PredAbsTransferRelation(TransferRelation):
    def __init__(self, precision : set[pysmt.fnode]):
        self.precision = precision

    def get_abstract_successors(self, predecessor):
        raise NotImplementedError(
            "successors without edge not possible for Predicate Analysis!"
        )

    def get_abstract_successors_for_edge(self, predecessor, edge):
        old = predecessor.predicates
        result = []
        match edge.instruction.kind:
            case InstructionType.STATEMENT:
                formula = PredAbsPrecision.ssa_from_assign(edge, ssa_indices=predecessor.ssa_indices)
                print('statement edge: ', formula, 'for', ast.unparse(edge.instruction.expression))
                # TODO
                result = [PredAbsState(predecessor)]
            case InstructionType.ASSUMPTION:
                formula = PredAbsPrecision.ssa_from_assume(edge, ssa_indices=predecessor.ssa_indices)
                print('assume edge: ', formula, 'for', ast.unparse(edge.instruction.expression))
                # TODO
                result = [PredAbsState(predecessor)]
            case InstructionType.CALL | InstructionType.NONDET:
                # ignore this for now
                result = [PredAbsState(predecessor)]
            case _:
                result = [PredAbsState(predecessor)]

        assert result[0].predicates is not None, predecessor
        return result


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




