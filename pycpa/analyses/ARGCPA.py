#!/usr/bin/env python

from typing import Collection, Optional # Added Optional

from pycpa.cpa import CPA, AbstractState, WrappedAbstractState, TransferRelation, MergeOperator, StopOperator
from pycpa.cfa import Graphable, CFAEdge, CFANode, InstructionType # Added CFANode, InstructionType
from pycpa.analyses.LocationCPA import LocationState # Assuming LocationState is in pycpa.analyses

from pycpa import log

import ast
from graphviz import Digraph
import copy


class ARGState(AbstractState):
    index = 0

    def __init__(self, wrapped_state: AbstractState, 
                 parent: Optional['ARGState'] = None, 
                 creating_edge: Optional[CFAEdge] = None):
        self.wrapped_state = wrapped_state
        self.state_id = ARGState.index
        ARGState.index += 1
        self.parents = set()
        if parent:
            self.parents.add(parent)
            parent.children.add(self)
        self.children = set()
        self.creating_edge: Optional[CFAEdge] = creating_edge

    def get_creating_edge(self) -> Optional[CFAEdge]:
        return self.creating_edge

    def __str__(self):
        return f"N{self.state_id} | {self.wrapped_state}"

    def __eq__(self, other):
        if not isinstance(other, ARGState):
            return False
        return self.wrapped_state == other.wrapped_state
    
    def __hash__(self):
        return hash(self.wrapped_state)

    def get_location_node(self) -> CFANode:
        loc_state = WrappedAbstractState.get_substate(self.wrapped_state, LocationState)
        return loc_state.location if loc_state else None

    def get_parents(self): 
        return self.parents

    def get_successors(self):
        return self.children


class ARGTransferRelation(TransferRelation):
    def __init__(self, wrapped_transfer_relation: TransferRelation):
        self.wrapped_transfer_relation = wrapped_transfer_relation

    def get_abstract_successors(self, predecessor_arg_state: ARGState) -> Collection[ARGState]:
        """
        This method should ideally not be directly used by the CPAAlgorithm if edge-specific
        information (like the creating_edge for CEX path) is crucial.
        The CPAAlgorithm should iterate over CFA edges from the predecessor's location
        and call get_abstract_successors_for_edge.
        """
        results: list[ARGState] = []
        loc_state = WrappedAbstractState.get_substate(predecessor_arg_state.wrapped_state, LocationState)
        assert loc_state is not None and loc_state.location is not None
        
        current_cfa_node: CFANode = loc_state.location
        for cfa_edge in current_cfa_node.leaving_edges:
            results.extend(self.get_abstract_successors_for_edge(predecessor_arg_state, cfa_edge))
        return results

    def get_abstract_successors_for_edge(self, 
                                         predecessor_arg_state: ARGState, 
                                         edge: CFAEdge) -> Collection[ARGState]:
        result_arg_states = []
        
        for wrapped_successor_state in \
                self.wrapped_transfer_relation.get_abstract_successors_for_edge(
                    predecessor_arg_state.wrapped_state, edge):
            
            # Create a new ARGState, crucially storing the 'edge' that created it.
            new_arg_state = ARGState(wrapped_state=wrapped_successor_state, 
                                     parent=predecessor_arg_state, 
                                     creating_edge=edge)
            
            result_arg_states.append(new_arg_state)
        return result_arg_states


class ARGStopOperator(StopOperator):
    def __init__(self, wrapped_stop_operator: StopOperator):
        self.wrapped_stop_operator = wrapped_stop_operator

    def stop(self, e: AbstractState, reached: Collection[AbstractState]) -> bool:
        # Stop is based on the wrapped state.
        # 'e' is the new state, 'reached' is a collection of already existing ARGStates.
        is_stopped = self.wrapped_stop_operator.stop(
            e.wrapped_state, [r.wrapped_state for r in reached if isinstance(r, ARGState)] # Make sure to unwrap
        )
        return is_stopped


class ARGMergeOperator(MergeOperator):
    def __init__(self, wrapped_merge_operator: MergeOperator):
        self.wrapped_merge_operator = wrapped_merge_operator

    def merge(self, state1_arg: ARGState, state2_arg: ARGState) -> ARGState:
        # log.printer.log_debug(1, f"[ARGMergeOperator DEBUG] Attempting merge between N{state1_arg.state_id} and N{state2_arg.state_id}")
        wrapped_state1 = state1_arg.wrapped_state
        wrapped_state2 = state2_arg.wrapped_state
        
        # Merge the wrapped states
        merged_wrapped_state = self.wrapped_merge_operator.merge(wrapped_state1, wrapped_state2)

        if merged_wrapped_state == wrapped_state2:
            # state1_arg.is_covered_by = state2_arg # Mark for removal from waitlist
            return state2_arg # state1 is covered by state2
        
        elif merged_wrapped_state == wrapped_state1:
            # log.printer.log_debug(1, f"[ARGMergeOperator DEBUG]   Wrapped states merged. Original state1_arg N{state1_arg.state_id}, state2_arg N{state2_arg.state_id}.")
            parents = state1_arg.parents.union(state2_arg.parents)
            children = state1_arg.children.union(state2_arg.children)
            
            if merged_wrapped_state is not wrapped_state1 and merged_wrapped_state is not wrapped_state2:
                 # A truly new merged state content was created by the wrapped merge operator
                log.printer.log_debug(1, f"[ARGMergeOperator INFO]   Wrapped merge created new content. Creating new ARGState.")
                new_arg_state = ARGState(merged_wrapped_state, creating_edge=state2_arg.creating_edge) # Edge is ambiguous

                # Re-wire parents
                for p in state1_arg.parents: p.children.discard(state1_arg); p.children.add(new_arg_state); new_arg_state.parents.add(p)
                for p in state2_arg.parents: p.children.discard(state2_arg); p.children.add(new_arg_state); new_arg_state.parents.add(p)
                # Re-wire children
                for c in state1_arg.children: c.parents.discard(state1_arg); c.parents.add(new_arg_state); new_arg_state.children.add(c)
                for c in state2_arg.children: c.parents.discard(state2_arg); c.parents.add(new_arg_state); new_arg_state.children.add(c)
                
                state1_arg.parents.clear(); state1_arg.children.clear()
                state2_arg.parents.clear(); state2_arg.children.clear()

                return new_arg_state # Indicates a new state was formed
            elif merged_wrapped_state is wrapped_state1: # state1 effectively covers state2 after merge
                log.printer.log_debug(1, f"[ARGMergeOperator DEBUG]   Merge resulted in state1_arg (N{state1_arg.state_id}) absorbing state2_arg (N{state2_arg.state_id}).")
                if state1_arg is not state2_arg : # Avoid self-merge issues with sets
                    for p in state2_arg.parents:
                        if p not in state1_arg.parents:
                            p.children.discard(state2_arg)
                            p.children.add(state1_arg)
                            state1_arg.parents.add(p)
                    for c in state2_arg.children:
                        if c not in state1_arg.children:
                            c.parents.discard(state2_arg)
                            c.parents.add(state1_arg)
                            state1_arg.children.add(c)
                    state2_arg.parents.clear(); state2_arg.children.clear()
                return state1_arg

            # If merged_wrapped_state is wrapped_state2, it was handled by the first if.
            # This path should not be reached if merged_wrapped_state is wrapped_state2 here.
            log.printer.log_debug(1, f"[ARGMergeOperator WARN]   Merge logic fell through, returning state2_arg N{state2_arg.state_id} by default.")
            return state2_arg # Default if no structural change to ARG based on wrapped merge.

        # This case should not be reached if the above handles all.
        log.printer.log_debug(1, f"[ARGMergeOperator WARN] Complex merge case not fully handled, returning state2_arg by default.")
        return state2_arg


class ARGCPA(CPA):
    def __init__(self, wrapped_cpa: CPA):
        self.wrapped_cpa = wrapped_cpa
        self.arg_root: Optional[ARGState] = None 

    def get_initial_state(self) -> ARGState:
        # The initial wrapped state (e.g. CompositeState(LocationState, PredAbsState))
        initial_wrapped = self.wrapped_cpa.get_initial_state()
        # Create the root ARGState. It has no parent and no creating_edge.
        root = ARGState(wrapped_state=initial_wrapped, parent=None, creating_edge=None)
        self.arg_root = root
        return root

    def get_stop_operator(self) -> StopOperator:
        return ARGStopOperator(self.wrapped_cpa.get_stop_operator())

    def get_merge_operator(self) -> MergeOperator:
        return ARGMergeOperator(self.wrapped_cpa.get_merge_operator())

    def get_transfer_relation(self) -> TransferRelation:
        return ARGTransferRelation(self.wrapped_cpa.get_transfer_relation())


# For visualization of the resulting ARG
class GraphableARGState(Graphable):
    def __init__(self, arg_state: ARGState):
        assert isinstance(arg_state, ARGState), f"Expected ARGState, got {type(arg_state)}"
        self.arg_state = arg_state

    @property
    def wrapped_state(self):
        return self.arg_state

    def get_node_label(self) -> str:
        return f"N{self.arg_state.state_id}\n{self.arg_state.wrapped_state}"


    def get_edge_labels(self, other: 'GraphableARGState') -> Collection[str]:
        # The edge label should come from the CFAEdge that created the 'other' state (child)
        # from 'self' state (parent).
        creating_edge = other.arg_state.get_creating_edge()
        if creating_edge and self.arg_state in other.arg_state.get_parents():
            return [creating_edge.label()]

        # Fallback if creating_edge is not definitive or for other edge types
        # It might not always be correct for interprocedural or complex CPAs.
        loc1_node = self.arg_state.get_location_node()
        loc2_node = other.arg_state.get_location_node()
        if loc1_node and loc2_node:
            for leaving_edge in loc1_node.leaving_edges:
                # Direct successor match
                if leaving_edge.successor == loc2_node:
                    return [leaving_edge.label()]
                # Call instruction match (LocationCPA jumps to function entry)
                if leaving_edge.instruction.kind == InstructionType.CALL and \
                   hasattr(leaving_edge.instruction, 'location') and \
                   leaving_edge.instruction.location == loc2_node:
                    return [leaving_edge.label()]
        return ["?"]

    def get_location_node(self) -> Optional[CFANode]: # Helper for get_edge_labels
        return self.arg_state.get_location_node()


    def get_successors(self) -> list['GraphableARGState']:
        return [GraphableARGState(child) for child in self.arg_state.children]

    def __eq__(self, other):
        if not isinstance(other, GraphableARGState):
            return False
        return self.arg_state == other.arg_state

    def get_node_id(self) -> int:
        return self.arg_state.state_id

    def __hash__(self):
        return hash(self.arg_state)
