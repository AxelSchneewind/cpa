#!/usr/bin/env python

from pycpa.cpa import CPA, AbstractState, WrappedAbstractState, TransferRelation, MergeOperator, StopOperator
from pycpa.cfa import Graphable, CFAEdge, InstructionType
from pycpa.analyses import LocationState, ValueState

import ast
import astpretty
from graphviz import Digraph

import copy
from typing import Collection


class StackState(WrappedAbstractState):
    def __init__(self, stack, parent=None):
        self.stack = stack
        
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
        return WrappedAbstractState.unwrap(self.stack[-1])
    

class StackTransferRelation(TransferRelation):
    def __init__(self, wrapped_transfer_relation):
        self.wrapped_transfer_relation = wrapped_transfer_relation

    def get_abstract_successors(self, predecessor):
        raise NotImplementedError('successors without edge unsupported for stack')

    def get_abstract_successors_for_edge(self, predecessor : StackState, edge):
        states = [
            wrapped_successor
            for wrapped_successor in self.wrapped_transfer_relation.get_abstract_successors_for_edge(
                predecessor.stack[-1], edge
            )
        ]
        result = [StackState(copy.deepcopy(predecessor.stack)) for w in states]

        kind = edge.instruction.kind
        if kind == InstructionType.CALL:
            for i, wrapped_successor in enumerate(states):
                result[i].stack.append(wrapped_successor)

        elif kind == InstructionType.RETURN:
            for i, wrapped_successor in enumerate(states):
                # advance instruction pointer 
                s = result[i].stack[-2]
                for w, p in zip(WrappedAbstractState.unwrap_fully(s), WrappedAbstractState.unwrap_fully(predecessor.stack[-2])):
                    if isinstance(p, LocationState):
                        w.location = p.location.leaving_edges[0].successor
                for w, p in zip(WrappedAbstractState.unwrap_fully(s), WrappedAbstractState.unwrap_fully(predecessor.stack[-1])):
                    if isinstance(p, ValueState):
                        if '__ret' in p.valuation:
                            w.valuation['__ret'] = copy.copy(p.valuation['__ret'])

                result[i].stack.pop()
            return result

        for i, wrapped_successor in enumerate(states):
            result[i].stack[-1] = wrapped_successor

        assert isinstance(result, list)
        return result


class StackStopOperator(StopOperator):
    def __init__(self, wrapped_stop_operator):
        self.wrapped_stop_operator = wrapped_stop_operator

    def stop(self, e : StackState, reached : Collection[StackState]) -> StackState:
        return self.wrapped_stop_operator.stop(
            e.stack[-1], [eprime.stack[-1] for eprime in reached]
        )



class StackMergeOperator(MergeOperator):
    def __init__(self, wrapped_merge_operator):
        self.wrapped_merge_operator = wrapped_merge_operator

    def merge(self, state1, state2):
        return state2
        # # merge upper stack frame
        # wrapped_state1 = state1.stack[-1]
        # wrapped_state2 = state2.stack[-1]
        # upper_merge_result = self.wrapped_merge_operator.merge(wrapped_state1, wrapped_state2)

        # # merge stack by suffix-relation

        # if upper_merge_result == wrapped_state2:
        #     return state2
        # else:
        #     state2[-1] = upper_merge_result
        #     return state2




class StackCPA(CPA):
    def __init__(self, wrapped_cpa):
        self.wrapped_cpa = wrapped_cpa

    def get_initial_state(self):
        return StackState([self.wrapped_cpa.get_initial_state()])

    def get_stop_operator(self):
        return StackStopOperator(self.wrapped_cpa.get_stop_operator())

    def get_merge_operator(self):
        return StackMergeOperator(self.wrapped_cpa.get_merge_operator())

    def get_transfer_relation(self):
        return StackTransferRelation(self.wrapped_cpa.get_transfer_relation())
