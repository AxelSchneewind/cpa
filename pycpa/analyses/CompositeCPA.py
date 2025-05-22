#!/usr/bin/env python

# ### CompositeCPA: Achieving synergy with several CPAs
# 
# Several CPAs can be used in parallel to achieve synergy.
# For this purpose, we need `CompositeCPA`, which is given in the next cell.
# `CompositeCPA` delegates the merge and stop operations to the corresponding merge and stop operators of each component CPA.
# The implementation is given, and you can proceed to the next task.

# In[19]:

from pycpa.cpa import AbstractState, WrappedAbstractState, TransferRelation, MergeOperator, CPA
from pycpa.analyses import LocationCPA
from pycpa.analyses import LocationState

import itertools
import copy

class CompositeState(WrappedAbstractState):
    def __init__(self, wrapped_states):
        assert isinstance(wrapped_states, list) or isinstance(wrapped_states, set) or isinstance(wrapped_states, tuple), type(wrapped_states)
        assert len(wrapped_states) > 0
        self.wrapped_states = wrapped_states

    def is_target(self):
        return any(
            [
                hasattr(state, "is_target") and state.is_target()
                for state in self.wrapped_states
            ]
        )

    def __eq__(self, other):
        assert type(self) == type(other)
        if other is self:
            return True
        if len(self.wrapped_states) != len(other.wrapped_states):
            return False
        return all(a == b for (a, b) in zip(self.wrapped_states, other.wrapped_states))

    def __hash__(self):
        return tuple(
            wrapped_state.__hash__() for wrapped_state in self.wrapped_states
        ).__hash__()

    def __str__(self):
        if any((isinstance(w, WrappedAbstractState) for w in self.wrapped_states)):
            return " %s " % "\n".join([str(state) for state in self.wrapped_states])
        else:
            return "(%s)" % ", ".join([str(state) for state in self.wrapped_states])
    
    def __deepcopy__(self, memo):
        return CompositeState(copy.deepcopy(self.wrapped_states))
    

class CompositeStopOperator(AbstractState):
    def __init__(self, wrapped_stop_operators):
        self.wrapped_stop_operators = wrapped_stop_operators

    def stop(self, e, reached):
        return any( # Exists any reached state that covers e?
                   all(# All components of e are covered by the corresponding component of eprime?
                       stop_op.stop(e_inner, [eprime_inner])
                       for stop_op, e_inner, eprime_inner in zip(self.wrapped_stop_operators, e.wrapped_states, eprime.wrapped_states)
                   )
                   for eprime in reached
               )


class CompositeTransferRelation(TransferRelation):
    def __init__(self, wrapped_transfer_relations):
        self.wrapped_transfer_relations = wrapped_transfer_relations

    def get_abstract_successors(self, predecessor):
        location_states = [
            state
            for state in WrappedAbstractState.get_substates(predecessor, LocationState)
        ]
        if len(location_states) == 0:
            return [
                CompositeState(product)
                for product in itertools.product(
                    *[
                        transfer.get_abstract_successors(state)
                        for (transfer, state) in zip(
                            self.wrapped_transfer_relations, predecessor.wrapped_states
                        )
                    ]
                )
            ]
        else:
            location_state = location_states[0]
            result = list()
            for edge in location_state.location.leaving_edges:
                result += self.get_abstract_successors_for_edge(predecessor, edge)
            return result

    def get_abstract_successors_for_edge(self, predecessor, edge):
        return [
            CompositeState(product)
            for product in itertools.product(
                *[
                    transfer.get_abstract_successors_for_edge(state, edge)
                    for (transfer, state) in zip(
                        self.wrapped_transfer_relations, predecessor.wrapped_states
                    )
                ]
            )
        ]


class CompositeMergeOperator(MergeOperator):
    """
    Merge-Agree: All wrapped states are merged pairwise.
    Example:

        merge((l, e), (l', e')) = (merge_L(l, l'), merge_E(e, e'))

    If any of the resulting merges does not cover both its input states
    (i.e., e \\leq merge_E(e, e') and e' \\leq merge_E(e, e'))
    then the second input (e.g., (l', e')) is returned.
    """

    def __init__(self, wrapped_merge_operators, wrapped_stop_operators):
        self.wrapped_merge_operators = wrapped_merge_operators
        self.wrapped_stop_operators = wrapped_stop_operators

    def merge(self, state1, state2):
        merge_results = list()
        wrapped_states1 = state1.wrapped_states
        wrapped_states2 = state2.wrapped_states
        for s1, s2, merge_operator, stop_operator in zip(
            wrapped_states1, wrapped_states2, self.wrapped_merge_operators, self.wrapped_stop_operators
        ):
            merge_result = merge_operator.merge(s1, s2)
            # Use the stop operator to check whether the merge result covers s1.
            # If it does not, we prevent merging for all wrapped states and return
            # state2.
            if not stop_operator.stop(s1, [merge_result]):
                return state2
            merge_results.append(merge_result)
        if all(sold == snew for sold, snew in zip(wrapped_states2, merge_results)):
            # If all merges were merge^sep, there's no need to create a new object
            # and we return state2.
            return state2
        return CompositeState(merge_results)


class CompositeCPA(CPA):
    def __init__(self, wrapped_cpas):
        self.wrapped_cpas = wrapped_cpas

    def get_initial_state(self):
        return CompositeState(
            [wrapped_cpa.get_initial_state() for wrapped_cpa in self.wrapped_cpas]
        )

    def get_stop_operator(self):
        return CompositeStopOperator(
            [wrapped_cpa.get_stop_operator() for wrapped_cpa in self.wrapped_cpas]
        )

    def get_merge_operator(self):
        return CompositeMergeOperator(
            [cpa.get_merge_operator() for cpa in self.wrapped_cpas],
            [cpa.get_stop_operator() for cpa in self.wrapped_cpas]
        )

    def get_transfer_relation(self):
        return CompositeTransferRelation(
            [wrapped_cpa.get_transfer_relation() for wrapped_cpa in self.wrapped_cpas]
        )



