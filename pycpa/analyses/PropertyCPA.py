#!/usr/bin/env python

from pycpa.cpa import CPA, AbstractState, TransferRelation, MergeOperator, StopOperator, MergeSepOperator
from pycpa.cfa import InstructionType, CFAEdge

import ast

class PropertyState(AbstractState):
    """ Abstracts for tracking if 'reach_error' has been called """
    def __init__(self, is_safe):
        self.safe = is_safe

    def subsumes(self, other) -> bool:
        return other.safe == None or self.safe == other.safe

    def __eq__(self, other):
        return self.safe == other.safe

    def __hash__(self):
        return self.safe.__hash__()

    def __str__(self):
        if self.safe:
            return 'safe'
        else:
            return 'unsafe'


class PropertyTransferRelation(TransferRelation):
    def get_abstract_successors(self, predecessor : AbstractState):
        raise NotImplementedError(
            "successors without edge not possible for Property Analysis!"
        )

    def get_abstract_successors_for_edge(self, predecessor : AbstractState, edge : CFAEdge) -> list[AbstractState]:
        assert isinstance(predecessor, PropertyState)

        kind = edge.instruction.kind
        if kind == InstructionType.REACH_ERROR:
            return [PropertyState(False)]
        else:
            return [predecessor]


class PropertyStopOperator(StopOperator):
    def stop(self, e, reached):
        return e in reached


class PropertyCPA(CPA):
    def get_initial_state(self):
        return PropertyState(True)

    def get_stop_operator(self):
        return PropertyStopOperator()

    def get_merge_operator(self):
        # simply use merge sep
        return MergeSepOperator()

    def get_transfer_relation(self):
        return PropertyTransferRelation()


