#!/usr/bin/env python

from typing import List, Optional

from pycpa.task import Task, Result, Status
from pycpa.cpa import WrappedAbstractState, AbstractState
from pycpa.analyses import PropertyState, LocationState # Assuming LocationState is in pycpa.analyses
from pycpa.analyses.ARGCPA import ARGState # Assuming ARGState is in pycpa.analyses.ARGCPA
from pycpa.cfa import CFAEdge # Assuming CFAEdge is in pycpa.cfa
from pycpa.verdict import Verdict


class CPAAlgorithm:
    def __init__(self, cpa, specifications, task : Task, result : Result):
        self.cpa = cpa
        self.iterations = 0
        self.task = task
        self.result = result
        self.abstract_cex_edges: Optional[List[CFAEdge]] = None # To store the CEX path

    def run(self, entry: ARGState): # Entry is typically an ARGState
        print(f"\n[CPAAlgorithm INFO] Starting CPAAlgorithm.run with entry state: {entry.state_id if isinstance(entry, ARGState) else entry}")
        waitlist = set()
        reached = set() # Stores ARGStates

        waitlist.add(entry)
        reached.add(entry)
        
        loop_count = 0
        while len(waitlist) > 0:
            loop_count += 1

            e: ARGState = waitlist.pop() # e is an ARGState
            print(f"[CPAAlgorithm DEBUG] Popped state from waitlist: N{e.state_id}, Wrapped: {e.wrapped_state}")

            self.iterations += 1
            if self.task.max_iterations and self.iterations >= self.task.max_iterations:
                print("[CPAAlgorithm WARN] Max iterations reached.")
                self.result.status = Status.TIMEOUT
                self.result.verdict = Verdict.UNKNOWN
                return

            # Check for error before exploring successors
            # The property check should be on the wrapped state inside the ARGState
            property_substates = WrappedAbstractState.get_substates(e.wrapped_state, PropertyState)
            is_error_state = any(not s.safe for s in property_substates)

            if is_error_state:
                print(f"[CPAAlgorithm INFO] Error state N{e.state_id} found: {e.wrapped_state}")
                self.result.status = Status.OK
                self.result.verdict = Verdict.FALSE
                self.result.witness = e # The ARGState itself is the witness
                
                # Reconstruct and store the counterexample path
                print(f"[CPAAlgorithm INFO] Reconstructing error path for witness N{e.state_id}...")
                self.abstract_cex_edges = self.get_error_path_edges(entry, e)
                if self.abstract_cex_edges:
                    print(f"[CPAAlgorithm INFO] Successfully reconstructed CEX path with {len(self.abstract_cex_edges)} edges.")
                    for i, cex_edge in enumerate(self.abstract_cex_edges):
                        print(f"[CPAAlgorithm DEBUG]   CEX Edge {i}: {cex_edge.label()}")
                else:
                    print("[CPAAlgorithm WARN] Could not reconstruct CEX path.")
                return # Stop analysis

            # Explore successors
            print(f"[CPAAlgorithm DEBUG] Exploring successors of N{e.state_id}...")
            successors_generated = 0
            for e_prime_arg in self.cpa.get_transfer_relation().get_abstract_successors(e): # e_prime_arg is also an ARGState
                successors_generated +=1
                print(f"[CPAAlgorithm DEBUG]   Generated successor: N{e_prime_arg.state_id}, Wrapped: {e_prime_arg.wrapped_state}")
                                
                to_add_to_waitlist = True # Assume we add unless merged or stopped
                
                merged_with_existing = False
                states_to_remove_from_reached = set()
                states_to_add_to_reached = set()

                # Stop Operator: Checks if e_prime_arg (or its wrapped state) is covered by anything in 'reached'
                if self.cpa.get_stop_operator().stop(e_prime_arg, reached):
                    print(f"[CPAAlgorithm DEBUG]     Stop operator covered N{e_prime_arg.state_id}. Not adding to waitlist.")
                    to_add_to_waitlist = False
                else:                  
                    # A more explicit merge loop (if ARGCPA doesn't fully integrate it into stop/transfer):
                    merged_e_prime_arg = e_prime_arg 
                    for e_reached_arg in list(reached): # Iterate over a copy for safe modification
                        # The merge op of ARGCPA takes ARGStates and returns an ARGState
                        potential_merge_result = self.cpa.get_merge_operator().merge(e_prime_arg, e_reached_arg)
                        
                        if potential_merge_result is not e_reached_arg: # Merge occurred and e_reached_arg was modified or replaced
                            print(f"[CPAAlgorithm DEBUG]     State N{e_prime_arg.state_id} merged with N{e_reached_arg.state_id}. Result: N{potential_merge_result.state_id}")
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
                        print(f"[CPAAlgorithm DEBUG]     Adding N{merged_e_prime_arg.state_id} to waitlist and reached.")
                        waitlist.add(merged_e_prime_arg) # Add the state that survived merge/stop
                        reached.add(merged_e_prime_arg)   # Add to reached set

            print(f"[CPAAlgorithm DEBUG]   Finished exploring successors of N{e.state_id}. Generated {successors_generated} direct successors.")


        if not waitlist: # Double check if error state was the last one processed
             property_substates_final_check = WrappedAbstractState.get_substates(e.wrapped_state, PropertyState)
             is_error_state_final_check = any(not s.safe for s in property_substates_final_check)
             if is_error_state_final_check and not self.result.verdict == Verdict.FALSE:
                print(f"[CPAAlgorithm INFO] Error state N{e.state_id} was the last in waitlist: {e.wrapped_state}")
                self.result.status = Status.OK
                self.result.verdict = Verdict.FALSE
                self.result.witness = e 
                self.abstract_cex_edges = self.get_error_path_edges(entry, e)
                return


        print(f"[CPAAlgorithm DEBUG] Waitlist size: {len(waitlist)}, Reached size: {len(reached)}")


        if self.result.verdict == Verdict.FALSE: # Error found by a successor
            print(f"[CPAAlgorithm INFO] Exiting run method because an error was found by a successor.")
            return

        if not waitlist and self.result.verdict != Verdict.FALSE:
            print("[CPAAlgorithm INFO] Waitlist is empty and no error found. Program is SAFE.")
            self.result.status = Status.OK
            self.result.verdict = Verdict.TRUE
            return
            
        print(f"[CPAAlgorithm DEBUG] End of while loop iteration. Waitlist size: {len(waitlist)}")

        # Final check after loop finishes
        if self.result.verdict != Verdict.FALSE: # If loop finishes and no error found
            print("[CPAAlgorithm INFO] CPAAlgorithm run finished. Waitlist empty. Program is SAFE.")
            self.result.status = Status.OK
            self.result.verdict = Verdict.TRUE
        return


    def get_error_path_edges(self, root_node: ARGState, error_node: ARGState) -> Optional[List[CFAEdge]]:
        """
        Reconstructs the path of CFAEdges from the root_node to the error_node in the ARG.
        Assumes ARGState has 'parents' attribute and a method to get its LocationState.
        """
        if not isinstance(error_node, ARGState) or not isinstance(root_node, ARGState):
            print("[CPAAlgorithm ERROR] get_error_path_edges: error_node or root_node is not an ARGState.")
            return None

        path_edges: List[CFAEdge] = []
        current_arg_state: ARGState = error_node
        
        print(f"[CPAAlgorithm DEBUG] Reconstructing path from N{root_node.state_id} to N{error_node.state_id}")

        visited_in_path_reconstruction = set() # To detect cycles in ARG during reconstruction (should not happen for CEX)

        while current_arg_state != root_node and current_arg_state.get_parents():
            if current_arg_state in visited_in_path_reconstruction:
                print(f"[CPAAlgorithm ERROR] Cycle detected in ARG during CEX path reconstruction at N{current_arg_state.state_id}. Aborting.")
                return None # Error or malformed ARG
            visited_in_path_reconstruction.add(current_arg_state)

            parent_arg_state: ARGState = list(current_arg_state.get_parents())[0]
            print(f"[CPAAlgorithm DEBUG]   Current: N{current_arg_state.state_id}, Parent: N{parent_arg_state.state_id}")

            parent_loc_state = WrappedAbstractState.get_substate(parent_arg_state.wrapped_state, LocationState)
            current_loc_state = WrappedAbstractState.get_substate(current_arg_state.wrapped_state, LocationState)

            if not parent_loc_state or not current_loc_state:
                print("[CPAAlgorithm ERROR] Could not get LocationState from ARGState during CEX reconstruction.")
                return None

            parent_cfa_node: CFANode = parent_loc_state.location
            current_cfa_node: CFANode = current_loc_state.location
            
            print(f"[CPAAlgorithm DEBUG]     Parent Loc: {parent_cfa_node.node_id}, Current Loc: {current_cfa_node.node_id}")


            found_edge = None
            for leaving_edge in parent_cfa_node.leaving_edges:
                if leaving_edge.successor == current_cfa_node:
                    found_edge = leaving_edge
                    break
            
            if hasattr(current_arg_state, 'get_creating_edge') and callable(getattr(current_arg_state, 'get_creating_edge')):
                # Ideal: if ARGState stores the edge that created it (e.g., set by ARGTransferRelation)
                edge_candidate = current_arg_state.get_creating_edge()
                if edge_candidate and edge_candidate.predecessor == parent_cfa_node and edge_candidate.successor == current_cfa_node:
                     found_edge = edge_candidate
                else: 
                    print(f"[CPAAlgorithm WARN] creating_edge mismatch or not found for N{current_arg_state.state_id}")


            if not found_edge:
                 # Fallback: iterate through parent's leaving edges
                for edge_option in parent_cfa_node.leaving_edges:
                    next_loc_after_edge = edge_option.successor # Default next location
                    if edge_option.instruction.kind == edge_option.instruction.kind.CALL:
                        # LocationCPA jumps to function entry for a CALL
                        if hasattr(edge_option.instruction, 'location') and edge_option.instruction.location == current_cfa_node:
                           found_edge = edge_option
                           break
                    elif edge_option.successor == current_cfa_node:
                        found_edge = edge_option
                        break
            
            if not found_edge:
                print(f"[CPAAlgorithm ERROR] Failed to find CFAEdge between parent N{parent_arg_state.state_id} (loc {parent_cfa_node.node_id}) and current N{current_arg_state.state_id} (loc {current_cfa_node.node_id}).")
                return None


            path_edges.append(found_edge)
            current_arg_state = parent_arg_state
            
        if current_arg_state != root_node:
            print(f"[CPAAlgorithm ERROR] CEX path reconstruction did not reach root node. Stopped at N{current_arg_state.state_id}.")
            return None # Path did not lead back to root

        return list(reversed(path_edges))

