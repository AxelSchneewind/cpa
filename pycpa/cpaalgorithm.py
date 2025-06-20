#!/usr/bin/env python

from typing import List, Optional

from pycpa.task import Task, Result, Status
from pycpa.cpa import WrappedAbstractState, AbstractState
from pycpa.analyses import PropertyState, LocationState
from pycpa.analyses.ARGCPA import ARGState
from pycpa.cfa import CFANode, CFAEdge
from pycpa.verdict import Verdict

from pycpa import log


class CPAAlgorithm:
    def __init__(self, cpa, specifications, task : Task, result : Result):
        self.cpa = cpa
        self.iterations = 0
        self.task = task
        self.result = result
        self.abstract_cex_edges: Optional[List[CFAEdge]] = None # To store the CEX path

    def run(self, entry: ARGState): # Entry is typically an ARGState
        log.printer.log_debug(1, f"\n[CPAAlgorithm INFO] Starting CPAAlgorithm.run with entry state: {entry.state_id if isinstance(entry, ARGState) else entry}")
        waitlist = set()
        reached = set() # Stores ARGStates

        waitlist.add(entry)
        reached.add(entry)
        
        loop_count = 0
        while len(waitlist) > 0:
            loop_count += 1

            e: ARGState = waitlist.pop() # e is an ARGState
            log.printer.log_debug(1, f"[CPAAlgorithm DEBUG] Popped state from waitlist: N{e.state_id}, Wrapped: {e.wrapped_state}")

            self.iterations += 1
            if self.task.max_iterations and self.iterations >= self.task.max_iterations:
                log.printer.log_debug(1, "[CPAAlgorithm WARN] Max iterations reached.")
                self.result.status = Status.TIMEOUT
                self.result.verdict = Verdict.UNKNOWN
                return

            # Check for error before exploring successors
            property_substates = WrappedAbstractState.get_substates(e, PropertyState)
            is_error_state = any(not s.safe for s in property_substates)

            if is_error_state:
                log.printer.log_debug(5, f"[CPAAlgorithm INFO] Error state N{e.state_id} found: {e.wrapped_state}")
                self.result.status = Status.OK
                self.result.verdict = Verdict.FALSE
                self.result.witness = e # The ARGState itself is the witness
                
                # Reconstruct and store the counterexample path
                log.printer.log_debug(5, f"[CPAAlgorithm INFO] Reconstructing error path for witness N{e.state_id}...")
                self.abstract_cex_edges = self.get_error_path_edges(entry, e)
                assert self.abstract_cex_edges
                return # Stop analysis

            # Explore successors
            log.printer.log_debug(3, f"[CPAAlgorithm DEBUG] Exploring successors of N{e.state_id}...")
            successors_generated = 0
            for e_prime_arg in self.cpa.get_transfer_relation().get_abstract_successors(e): # e_prime_arg is also an ARGState
                successors_generated +=1
                log.printer.log_debug(3, f"[CPAAlgorithm DEBUG]   Generated successor: N{e_prime_arg.state_id}, Wrapped: {e_prime_arg.wrapped_state}")
                                
                to_add_to_waitlist = True # Assume we add unless merged or stopped
                
                merged_with_existing = False
                states_to_remove_from_reached = set()
                states_to_add_to_reached = set()

                # Stop Operator: Checks if e_prime_arg (or its wrapped state) is covered by anything in 'reached'
                if self.cpa.get_stop_operator().stop(e_prime_arg, reached):
                    log.printer.log_debug(3, f"[CPAAlgorithm DEBUG]     Stop operator covered N{e_prime_arg.state_id}. Not adding to waitlist.")
                    to_add_to_waitlist = False
                else:                  
                    # A more explicit merge loop (if ARGCPA doesn't fully integrate it into stop/transfer):
                    merged_e_prime_arg = e_prime_arg 
                    for e_reached_arg in list(reached): # Iterate over a copy for safe modification
                        # The merge op of ARGCPA takes ARGStates and returns an ARGState
                        potential_merge_result = self.cpa.get_merge_operator().merge(e_prime_arg, e_reached_arg)
                        
                        if potential_merge_result is not e_reached_arg: # Merge occurred and e_reached_arg was modified or replaced
                            log.printer.log_debug(1, f"[CPAAlgorithm DEBUG]     State N{e_prime_arg.state_id} merged with N{e_reached_arg.state_id}. Result: N{potential_merge_result.state_id}")
                            states_to_remove_from_reached.add(e_reached_arg)
                            if e_reached_arg in waitlist:
                                waitlist.remove(e_reached_arg)
                            
                            # The result of the merge is what we should consider further
                            merged_e_prime_arg = potential_merge_result 
                            pass # Handled by stop operator and ARGCPA internals for now.
                    
                    # After potential merges (which ARGCPA's stop/transfer might handle implicitly):
                    reached.difference_update(states_to_remove_from_reached)
                    # Add the (possibly merged) state if it's new to `reached`
                    if merged_e_prime_arg not in reached: # merged_e_prime_arg could be a new state or an existing one
                        states_to_add_to_reached.add(merged_e_prime_arg)
                    
                    if to_add_to_waitlist: # If not stopped
                        log.printer.log_debug(1, f"[CPAAlgorithm DEBUG]     Adding N{merged_e_prime_arg.state_id} to waitlist and reached.")
                        waitlist.add(merged_e_prime_arg) # Add the state that survived merge/stop
                        reached.add(merged_e_prime_arg)   # Add to reached set

            log.printer.log_debug(3, f"[CPAAlgorithm DEBUG]   Finished exploring successors of N{e.state_id}. Generated {successors_generated} direct successors.")

        log.printer.log_debug(1, f"[CPAAlgorithm DEBUG] Waitlist size: {len(waitlist)}, Reached size: {len(reached)}")

        if not waitlist and self.result.verdict != Verdict.FALSE:
            log.printer.log_debug(1, "[CPAAlgorithm INFO] Waitlist is empty and no error found. Program is SAFE.")
            self.result.status = Status.OK
            self.result.verdict = Verdict.TRUE
            return

        return


    def get_error_path_edges(self, root_node: ARGState, error_node: ARGState) -> Optional[List[CFAEdge]]:
        """
        Reconstructs the path of CFAEdges from the root_node to the error_node in the ARG.
        Assumes ARGState has 'parents' attribute and a method to get its LocationState.
        """
        assert isinstance(error_node, ARGState) and isinstance(root_node, ARGState)

        path_edges: List[CFAEdge] = []
        current_arg_state: ARGState = error_node
        
        log.printer.log_debug(1, f"[CPAAlgorithm DEBUG] Reconstructing path from N{root_node.state_id} to N{error_node.state_id}")

        visited_in_path_reconstruction = set() # To detect cycles in ARG during reconstruction (should not happen for CEX)

        while current_arg_state != root_node and current_arg_state.get_parents():
            assert current_arg_state not in visited_in_path_reconstruction
            visited_in_path_reconstruction.add(current_arg_state)

            parent_arg_state: ARGState = list(current_arg_state.get_parents())[0]

            parent_loc_state = WrappedAbstractState.get_substate(parent_arg_state.wrapped_state, LocationState)
            current_loc_state = WrappedAbstractState.get_substate(current_arg_state.wrapped_state, LocationState)
            assert parent_loc_state and current_loc_state

            parent_cfa_node: CFANode = parent_loc_state.location
            current_cfa_node: CFANode = current_loc_state.location
            
            assert hasattr(current_arg_state, 'get_creating_edge') 
            found_edge = current_arg_state.get_creating_edge()

            assert found_edge
            path_edges.append(found_edge)
            current_arg_state = parent_arg_state
            
        assert current_arg_state == root_node
        return list(reversed(path_edges))

