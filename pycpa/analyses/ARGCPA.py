#!/usr/bin/env python

# For keeping track of the predecessor-successor relationship among abstract states,
# we can wrap our CPAs into a CPA dedicated for constructing the *abstract reachability graph*, the `ARGCPA`:

# In[15]:

from pycpa.cpa import CPA, AbstractState, WrappedAbstractState, TransferRelation, MergeOperator, StopOperator
from pycpa.cfa import Graphable
from pycpa.analyses import LocationCPA

import ast
import astpretty
from graphviz import Digraph

import copy


class ARGState(AbstractState):
    index = 0

    def __init__(self, wrapped_state, parent=None):
        self.wrapped_state = wrapped_state
        self.state_id = ARGState.index
        ARGState.index += 1
        self.parents = set()
        if parent:
            self.parents.add(parent)
            parent.children.add(self)
        self.children = set()

    def __str__(self):
        return f"N{self.state_id} - {self.wrapped_state}"

    def is_target(self):
        return hasattr(self.wrapped_state, "is_target") and self.wrapped_state.is_target()


class ARGTransferRelation(TransferRelation):
    def __init__(self, wrapped_transfer_relation):
        self.wrapped_transfer_relation = wrapped_transfer_relation

    def get_abstract_successors(self, predecessor):
        result = [
            ARGState(wrapped_successor, predecessor)
            for wrapped_successor in self.wrapped_transfer_relation.get_abstract_successors(
                predecessor.wrapped_state
            )
        ]
        return result


class ARGStopOperator(StopOperator):
    def __init__(self, wrapped_stop_operator):
        self.wrapped_stop_operator = wrapped_stop_operator

    def stop(self, e, reached):
        return self.wrapped_stop_operator.stop(
            e.wrapped_state, [eprime.wrapped_state for eprime in reached]
        )



class ARGMergeOperator(MergeOperator):
    def __init__(self, wrapped_merge_operator):
        self.wrapped_merge_operator = wrapped_merge_operator

    def merge(self, state1, state2):
        wrapped_state1 = state1.wrapped_state
        wrapped_state2 = state2.wrapped_state
        merge_result = self.wrapped_merge_operator.merge(wrapped_state1, wrapped_state2)
        if (
            merge_result == wrapped_state2
        ):  # and (wrapped_state1 != wrapped_state2 or all(parent1 in state2.parents for parent1 in state1.parents)):
            return state2
        else:
            # merge both into a new state:
            parents = state1.parents.union(state2.parents)
            children = state1.children.union(state2.children)
            new_state = ARGState(merge_result)
            for state in (state1, state2):
                for parent in state.parents:
                    parent.children.discard(state)
                    parent.children.add(new_state)
                state.parents = set()
                for child in state.children:
                    child.parents.discard(state)
                    child.parents.add(new_state)
                state.children = set()
            new_state.children = children
            new_state.parents = parents
            return new_state


class ARGCPA(CPA):
    def __init__(self, wrapped_cpa):
        self.wrapped_cpa = wrapped_cpa

    def get_initial_state(self):
        return ARGState(self.wrapped_cpa.get_initial_state())

    def get_stop_operator(self):
        return ARGStopOperator(self.wrapped_cpa.get_stop_operator())

    def get_merge_operator(self):
        return ARGMergeOperator(self.wrapped_cpa.get_merge_operator())

    def get_transfer_relation(self):
        return ARGTransferRelation(self.wrapped_cpa.get_transfer_relation())


# For visualization of the resulting ARG, we can reuse the `Graphable` interface we used before:

# In[16]:


class GraphableARGState(Graphable):
    def __init__(self, arg_state):
        assert isinstance(arg_state, ARGState)
        self.arg_state = arg_state

    def get_node_label(self):
        return str("N%d\n%s" % (self.arg_state.state_id, self.arg_state.wrapped_state))

    def get_edge_labels(self, other):
        loc1 = self._extract_location(self)
        loc2 = self._extract_location(other)
        if loc1 and loc2:
            for leaving_edge in loc1.leaving_edges:
                if leaving_edge.successor == loc2:
                    return [leaving_edge.label()]
        if loc1 and len(loc1.leaving_edges) > 0:
            return [loc1.leaving_edges[0].label()]
        return ['']

    def _extract_location(self, state):
        waitlist = set()
        waitlist.add(state.arg_state)
        location = None
        while waitlist:
            current = waitlist.pop()
            waitlist.update(WrappedAbstractState.unwrap_fully(current))
            if isinstance(current, LocationCPA.LocationState):
                location = current.location
                break
        return location

    def get_successors(self):
        return [GraphableARGState(child) for child in self.arg_state.children]

    def __eq__(self, other):
        return self.arg_state == other.arg_state

    def __hash__(self):
        return self.arg_state.__hash__()


