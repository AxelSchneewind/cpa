#!/usr/bin/env python

from pycpa.cpa import CPA, AbstractState, WrappedAbstractState, TransferRelation, MergeOperator, StopOperator
from pycpa.cfa import Graphable, CFAEdge, InstructionType, Instruction
from pycpa.analyses import LocationState, ValueState

import ast
import astpretty 
from graphviz import Digraph
import copy
from typing import Collection


class StackState(WrappedAbstractState):
    def __init__(self, stack, call_edge_stack):
        self.stack = stack
        self.call_edge_stack = call_edge_stack

    def __deepcopy__(self, memo):
        stack = copy.deepcopy(self.stack)
        call_edge_stack = copy.copy(self.call_edge_stack)
        return StackState(stack, call_edge_stack)
        
    def __str__(self):
        return f"{self.stack[-1]}"

    def wrapped(self):
        return WrappedAbstractState.unwrap(self.stack[-1]) if len(self.stack) > 0 else []
    
    def __eq__(self, other):
        if not isinstance(other, StackState):
            return False
        if len(self.stack) != len(other.stack):
            return False
        return all(a == b for a,b in zip(self.stack, other.stack)) and all(a == b for a,b in zip(self.call_edge_stack, other.call_edge_stack))

    def __hash__(self):
        return (
            tuple(
                s.__hash__() for s in self.stack
            ).__hash__(),
            tuple(
                rv.__hash__() for rv in self.call_edge_stack
            ).__hash__()
        ).__hash__()
    

class StackTransferRelation(TransferRelation):
    def __init__(self, wrapped_transfer_relation):
        self.wrapped_transfer_relation = wrapped_transfer_relation

    def get_abstract_successors(self, predecessor):
        raise NotImplementedError('successors without edge unsupported for stack')


    def _handle_Call(self, predecessor : StackState, edge : CFAEdge):
        assert edge.instruction.kind == InstructionType.CALL
        
        states = [
            wrapped_successor
            for wrapped_successor in self.wrapped_transfer_relation.get_abstract_successors_for_edge(
                predecessor.stack[-1], edge
            )
        ]
        result = [ copy.deepcopy(predecessor) for w in states]

        for i, wrapped_successor in enumerate(states):
            # result[i].stack.append(wrapped_successor)
            result[i].stack[-1] = wrapped_successor
            result[i].call_edge_stack.append(edge)

        assert isinstance(result, list)
        return result

    def _handle_Return(self, predecessor : StackState, edge : CFAEdge):
        assert edge.instruction.kind == InstructionType.RETURN

        # exit program
        if len(predecessor.call_edge_stack) <= 1:
            return []

        states = [
            wrapped_successor
            for wrapped_successor in self.wrapped_transfer_relation.get_abstract_successors_for_edge(
                predecessor.stack[-1], edge
            )
        ]

        result = [ copy.deepcopy(predecessor) for w in states]
        for i,r in enumerate(result):
            loc = WrappedAbstractState.get_substate(states[i], LocationState)
            loc.location = result[i].call_edge_stack[-1].successor

            result[i].call_edge_stack.pop()
            result[i].stack[-1] = states[i]

        return result

    def get_abstract_successors_for_edge(self, predecessor : StackState, edge : CFAEdge):
        kind = edge.instruction.kind
        if kind == InstructionType.CALL:
            return self._handle_Call(predecessor, edge)
        elif kind == InstructionType.RETURN:
            return self._handle_Return(predecessor, edge)
        else:
            states = [
                wrapped_successor
                for wrapped_successor in self.wrapped_transfer_relation.get_abstract_successors_for_edge(
                    predecessor.stack[-1], edge
                )
            ]
            result = [ copy.deepcopy(predecessor) for w in states]

            for i, wrapped_successor in enumerate(states):
                result[i].stack[-1] = wrapped_successor

            assert isinstance(result, list)
            return result


class StackStopOperator(StopOperator[StackState]):
    def __init__(self, wrapped_stop_operator : StopOperator):
        self.wrapped_stop_operator = wrapped_stop_operator

    def stop(self, e : StackState, reached : Collection[StackState]) -> bool:
        return any( # Exists any reached state that covers e?
                   all(# All frames of e are covered by the corresponding component of eprime?
                       self.wrapped_stop_operator.stop(e_inner, [eprime_inner])
                       for e_inner, eprime_inner in zip(e.stack, eprime.stack)
                   )
                   for eprime in reached if len(e.stack) == len(eprime.stack)
               )


class StackMergeOperator(MergeOperator[StackState]):
    def __init__(self, wrapped_merge_operator : MergeOperator):
        self.wrapped_merge_operator = wrapped_merge_operator

    def merge(self, state1 : StackState, state2 : StackState) -> StackState:
        # merge only if lower stack frames are equal
        if len(state1.stack) == len(state2.stack) > 0 and all(a == b for a,b in zip(state1.stack[:-1], state2.stack[:-1])):
            frame = self.wrapped_merge_operator.merge(state1.stack[-1], state2.stack[-1])
            if frame != state2.stack[-1]:
                state1.stack[-1] = frame
                return state1

        return state2


class StackCPA(CPA[StackState]):
    def __init__(self, wrapped_cpa):
        self.wrapped_cpa = wrapped_cpa

    def get_initial_state(self):
        return StackState([self.wrapped_cpa.get_initial_state()], [None])

    def get_stop_operator(self):
        return StackStopOperator(self.wrapped_cpa.get_stop_operator())

    def get_merge_operator(self):
        return StackMergeOperator(self.wrapped_cpa.get_merge_operator())

    def get_transfer_relation(self):
        return StackTransferRelation(self.wrapped_cpa.get_transfer_relation())
