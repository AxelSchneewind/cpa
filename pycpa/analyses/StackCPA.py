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
        if len(self.stack) > 0:
            if len(self.stack) > 2:
                stacks = '\n'.join(reversed([str(s) for s in self.stack[-3:]]))
                return f"{stacks}\n..."
            if len(self.stack) <= 2:
                stacks = '\n'.join(reversed([str(s) for s in self.stack]))
                return f"{stacks}"
        else:
            return f"..."

    def is_target(self):
        return hasattr(self.stack[-1], "is_target") and self.stack[-1].is_target()
    
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
            result[i].stack.append(wrapped_successor)
            result[i].call_edge_stack.append(edge)

        assert isinstance(result, list)
        return result

    def _handle_Return(self, predecessor : StackState, edge : CFAEdge):
        assert edge.instruction.kind == InstructionType.RETURN

        if len(predecessor.stack) < 2:
            return []

        call_edge = predecessor.call_edge_stack[-1]
        virt_edge = copy.copy(call_edge)

        virt_edge.instruction = Instruction.resume(call_edge.instruction.expression, predecessor.stack[-1], call_edge, edge)

        # use virtual edge
        states = [
            wrapped_successor
            for wrapped_successor in self.wrapped_transfer_relation.get_abstract_successors_for_edge(
                predecessor.stack[-2], virt_edge
            )
        ]

        result = [ copy.deepcopy(predecessor) for w in states]
        for i,r in enumerate(result):
            result[i].stack.pop()
            result[i].call_edge_stack.pop()
            result[i].stack[-1] = states[i]

        # for i, wrapped_successor in enumerate(states):
        #     # advance instruction pointer 
        #     s = result[i].stack[-1]
        #     for w in WrappedAbstractState.get_substates(s, LocationState):
        #         assert len(w.location.leaving_edges) <= 1   # assume unique successor edge
        #         if len(w.location.leaving_edges) > 0:
        #             w.location = w.location.leaving_edges[0].successor

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

            # only for non-return edges: update uppermost stack frame
            for i, wrapped_successor in enumerate(states):
                result[i].stack[-1] = wrapped_successor

            assert isinstance(result, list)
            return result


class StackStopOperator(StopOperator):
    def __init__(self, wrapped_stop_operator):
        self.wrapped_stop_operator = wrapped_stop_operator

    def stop(self, e : StackState, reached : Collection[StackState]) -> StackState:
        return any( # Exists any reached state that covers e?
                   all(# All frames of e are covered by the corresponding component of eprime?
                       self.wrapped_stop_operator.stop(e_inner, [eprime_inner])
                       for e_inner, eprime_inner in zip(e.stack, eprime.stack)
                   )
                   for eprime in reached if len(e.stack) == len(eprime.stack)
               )


class StackMergeOperator(MergeOperator):
    def __init__(self, wrapped_merge_operator):
        self.wrapped_merge_operator = wrapped_merge_operator

    def merge(self, state1, state2):
        # merge only if lower stack frames are equal
        if len(state1.stack) == len(state2.stack) > 0 and all(a == b for a,b in zip(state1.stack[:-1], state2.stack[:-1])):
            frame = self.wrapped_merge_operator.merge(state1.stack[-1], state2.stack[-1])
            if frame != state2.stack[-1]:
                state1.stack[-1] = frame
                return state1

        return state2


class StackCPA(CPA):
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
