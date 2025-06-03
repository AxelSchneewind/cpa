#!/bin/env/python

from pycpa.cpa import CPA
from pycpa.cpa import MergeSepOperator, StopSepOperator, AbstractState, TransferRelation

from pycpa.cfa import CFANode, CFAEdge, InstructionType

from typing import Collection


class LocationState(AbstractState):
    def __init__(self, node: CFANode):
        self.location = node

    def __str__(self):
        return f"@{self.location.node_id}"

    def __eq__(self, other):
        return self.location == other.location

    def __hash__(self):
        return hash(self.location)
    
    def __deepcopy__(self, memo):
        return LocationState(self.location)


class LocationTransferRelation(TransferRelation):

    def get_abstract_successors(self, predecessor: LocationState) -> Collection[LocationState]:
        return [
            LocationState(edge.successor) 
            for edge in predecessor.location.leaving_edges 
            if edge.kind is not InstructionType.CALL
        ] + [
            LocationState(edge.instruction.location) 
            for edge in predecessor.location.leaving_edges 
            if edge.kind is InstructionType.CALL
        ]

    def get_abstract_successors_for_edge(self, predecessor: LocationState, edge: CFAEdge) -> Collection[LocationState]:
        kind = edge.instruction.kind

        # for call, do not advance location state, this will happen on resume
        if kind == InstructionType.CALL:
            return [LocationState(edge.instruction.location)]
        if kind in { InstructionType.EXIT, InstructionType.ABORT }:
            return [LocationState(predecessor.location)]
        return [LocationState(edge.successor)]


class LocationStopOperator(StopSepOperator):
    def __init__(self):
        return StopSepOperator.__init__(self, LocationState.__eq__)


class LocationCPA(CPA):
    def __init__(self, cfa_root: CFANode):
        self.root = cfa_root

    def get_initial_state(self):
        return LocationState(self.root)

    def get_stop_operator(self):
        return LocationStopOperator()

    def get_merge_operator(self):
        return MergeSepOperator()

    def get_transfer_relation(self):
        return LocationTransferRelation()



