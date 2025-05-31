#!/usr/bin/env python3
"""
Predicate Abstraction with Counter-Example Guided Abstraction Refinement (CEGAR).
"""

from typing import List, Optional

from pycpa.cfa import CFANode, CFAEdge
from pycpa.cpa import CPA, WrappedAbstractState # For type hinting and utility
from pycpa.task import Task, Result, Status # Assuming these are defined in your project
from pycpa.verdict import Verdict

# CPAs
from pycpa.analyses import (
    LocationCPA,
    PredAbsCPA,
    PropertyCPA,
    CompositeCPA,
    ARGCPA
)
# Precision
from pycpa.analyses.PredAbsPrecision import PredAbsPrecision
# Algorithm
from pycpa.cpaalgorithm import CPAAlgorithm
# Helper for SMT an Interpolation
from pycpa.analyses import cegar_helper 

# For constructing the initial CPA stack
from pycpa.analyses.ARGCPA import ARGState, GraphableARGState
from pycpa.utils.visual import arg_to_dot

from pycpa import log


class PredAbsCEGARDriver:
    def __init__(self,
                 entry_node: CFANode,
                 cfa_roots: List[CFANode], # For initial precision
                 cpa_task: Task,
                 cpa_result: Result, # To store final result
                 max_refinements: int = 10,
                 initial_precision: Optional[PredAbsPrecision] = None):

        self.program_name = cpa_task.program
        log.printer.log_debug(1, f"\n[CEGAR Driver INFO] Initializing PredAbsCEGARDriver for '{self.program_name}'.")
        self.entry_node: CFANode = entry_node
        self.cfa_roots: List[CFANode] = cfa_roots # Used for PredAbsPrecision.from_cfa
        self.task: Task = cpa_task
        self.result: Result = cpa_result # This will be updated by the algorithm
        self.initial_arg_state = None

        self.max_refinements: int = max_refinements
        
        if initial_precision:
            self.current_precision: PredAbsPrecision = initial_precision
            log.printer.log_debug(1, "[CEGAR Driver INFO] Using provided initial precision.")
        else:
            log.printer.log_debug(1, "[CEGAR Driver INFO] Creating initial precision from CFA roots...")
            # Create an initial, possibly empty or globally-derived, precision
            self.current_precision = PredAbsPrecision.from_cfa(self.cfa_roots)
        log.printer.log_debug(1, f"[CEGAR Driver INFO] Initial precision state: {self.current_precision}")

        # The core CPA that will be refined (specifically, its PredAbsCPA component's precision)
        # This needs to be recreated or updated in each iteration if precision changes.
        self.pred_abs_cpa: Optional[PredAbsCPA] = None # Will be set in _build_cpa_stack
        self.analysis_cpa: Optional[ARGCPA] = None # The top-level ARGCPA

    def get_arg_root(self):
        return self.initial_arg_state

    def _build_cpa_stack(self) -> ARGCPA:
        """Builds the CPA stack with the current precision."""
        log.printer.log_debug(1, "[CEGAR Driver DEBUG] Building CPA stack...")
        
        # Ensure PredAbsCPA uses the most up-to-date precision
        self.pred_abs_cpa = PredAbsCPA(initial_precision=self.current_precision)
        log.printer.log_debug(1, f"[CEGAR Driver DEBUG]   PredAbsCPA created with precision: {self.current_precision}")

        location_cpa = LocationCPA(cfa_root=self.entry_node)
        # Specifications (like PropertyCPA) would be passed from the main script
        # For now, assuming PropertyCPA is handled by the main script's `cpas` list
        # and composed there. Here, we focus on Location x Predicate.
        # If PropertyCPA needs to be part of this CEGAR-specific stack, add it here.
        
        # Simplified: assuming specifications are handled by the `CPAAlgorithm` constructor
        # The `CompositeCPA` here should include all CPAs needed for the abstraction part.
        # The `specifications` passed to `CPAAlgorithm` will handle property checking.
        composite_cpa = CompositeCPA([location_cpa, self.pred_abs_cpa, PropertyCPA()])
        log.printer.log_debug(1, f"[CEGAR Driver DEBUG]   CompositeCPA created with: LocationCPA, PredAbsCPA")
        
        arg_cpa = ARGCPA(wrapped_cpa=composite_cpa)
        log.printer.log_debug(1, f"[CEGAR Driver DEBUG]   ARGCPA created, wrapping CompositeCPA.")
        self.analysis_cpa = arg_cpa
        return arg_cpa

    def run_cegar(self, specifications_cpas: List[CPA]):
        """
        Executes the CEGAR loop.
        specifications_cpas: CPAs like PropertyCPA for checking the safety property.
        """
        log.printer.log_debug(5, f"\n[CEGAR Driver INFO] Starting CEGAR loop for '{self.program_name}'. Max refinements: {self.max_refinements}")

        for i in range(self.max_refinements):
            log.printer.log_debug(5, f"CEGAR Iteration {i + 1}/{self.max_refinements}")

            # 1. Build CPA stack with current precision
            # The analysis_cpa (ARGCPA) will wrap a CompositeCPA containing LocationCPA and PredAbsCPA(self.current_precision)
            # It's important that PredAbsCPA uses the *updated* self.current_precision.
            current_arg_cpa_config = self._build_cpa_stack()
            
            # The specifications_cpas (e.g., PropertyCPA) are added to the CompositeCPA by the main runner usually.
            # Here, we need to ensure the CPAAlgorithm gets a CPA that includes both the abstraction
            # CPAs (Location, Predicate) and the specification CPAs.
            # Let's assume the main script will create a final CompositeCPA that includes
            # current_arg_cpa_config's *wrapped* CPA and the specification_cpas.
            # Or, more simply, CPAAlgorithm takes the ARGCPA and a separate list of spec CPAs.
            # The provided CPAAlgorithm takes `cpa` (the ARGCPA) and `specifications` (list of spec CPAs).
            # The ARGCPA should internally wrap the (LocationCPA+PredAbsCPA).
            # The PropertyCPA is handled by the CPAAlgorithm by checking substates.

            # Create a fresh result object for this iteration's algorithm run
            # The main `self.result` will be updated with the final outcome.
            iteration_result = Result() 
            algo = CPAAlgorithm(cpa=current_arg_cpa_config,
                                specifications=specifications_cpas, # e.g. [PropertyCPA_instance]
                                task=self.task, # Use the main task
                                result=iteration_result) # Algo updates this iteration_result

            # 2. Run the CPAAlgorithm
            # ARGCPA.get_initial_state() creates the root ARGState
            self.initial_arg_state: ARGState = current_arg_cpa_config.get_initial_state()
            log.printer.log_debug(5, f"[CEGAR Driver INFO] Running CPAAlgorithm for iteration {i + 1}...")
            algo.run(self.initial_arg_state) # Algorithm updates iteration_result

            with open(self.task.output_directory + '/precision_' + str(i), 'w') as f:
                f.write(str(self.current_precision))


            arg = GraphableARGState(self.initial_arg_state)
            dot = arg_to_dot(
                    [ arg ],
                    nodeattrs={"style": "filled", "shape": "box", "color": "white"},
                )
            dot.render(self.task.output_directory + '/arg_' + str(i))

            # 3. Check Algorithm's Result for this iteration
            log.printer.log_debug(5, f"[CEGAR Driver INFO] CPAAlgorithm finished. Iteration Verdict: {iteration_result.verdict}, Status: {iteration_result.status}")

            if iteration_result.verdict == Verdict.TRUE:
                self.result.verdict = Verdict.TRUE # Update main result
                self.result.status = Status.OK
                log.printer.log_intermediate_result(self.program_name, str(self.result.status), str(self.result.verdict))
                return # Program is safe

            if iteration_result.status == Status.TIMEOUT:
                self.result.verdict = Verdict.UNKNOWN
                self.result.status = Status.TIMEOUT
                log.printer.log_intermediate_result(self.program_name, str(self.result.status), str(self.result.verdict))
                return # Timeout

            if iteration_result.verdict == Verdict.FALSE:
                # Abstract counterexample found by the algorithm
                abstract_cex: Optional[List[CFAEdge]] = algo.abstract_cex_edges
                if not abstract_cex:
                    log.printer.log_debug(5, "[CEGAR Driver ERROR] Algorithm reported FALSE but no CEX path found. Treating as UNKNOWN.")
                    self.result.verdict = Verdict.UNKNOWN
                    self.result.status = Status.OK
                    log.printer.log_intermediate_result(self.program_name, str(self.result.status), str(self.result.verdict) + '(Error in CEX generation)')
                    return

                log.printer.log_debug(5, f"[CEGAR Driver INFO] Abstract counterexample found with {len(abstract_cex)} edges.")
                
                # 4. Check Feasibility of the Abstract CEX
                is_feasible, path_formula_conjuncts = cegar_helper.is_path_feasible(abstract_cex)

                with open(self.task.output_directory + '/cex_' + str(i), 'w') as f:
                    f.write(str(path_formula_conjuncts))

                if is_feasible:
                    self.result.verdict = Verdict.FALSE # Update main result
                    self.result.status = Status.OK
                    log.printer.log_intermediate_result(self.program_name, str(self.result.status), str(self.result.verdict))
                    # TODO: Store concrete CEX if model was extracted by is_path_feasible
                    return # Real counterexample

                # 5. Spurious CEX: Refine Precision
                log.printer.log_debug(5, "[CEGAR Driver INFO] Abstract counterexample is SPURIOUS. Refining precision...")
                if path_formula_conjuncts is None:
                    log.printer.log_debug(5, "[CEGAR Driver ERROR] Path was spurious but no path formula conjuncts for interpolation. Cannot refine.")
                    self.result.status = Status.ERROR
                    self.result.verdict = Verdict.UNKNOWN
                    log.printer.log_intermediate_result(self.program_name, str(self.result.status) + '(Error in SMT for interpolation)', str(self.result.verdict))
                    return
                
                # The self.current_precision object is updated in-place by refine_precision
                # if it modifies its internal dicts. Or it returns a new object.
                # PredAbsPrecision.add_local_predicates_map modifies in-place.
                new_precision = cegar_helper.refine_precision(
                    current_precision=self.current_precision, # Pass the PredAbsPrecision object
                    abstract_cex_edges=abstract_cex,
                    path_formula_conjuncts=path_formula_conjuncts
                )
                log.printer.log_debug(5, f"[CEGAR Driver INFO] Precision updated. New state: {self.current_precision}")
                # The loop will continue, and _build_cpa_stack will use the updated self.current_precision

                if new_precision is self.current_precision:
                    log.printer.log_debug(1, 'CEGAR Driver INFO', "Could not refine. Fixpoint reached")
                    self.result.verdict = Verdict.FALSE
                    self.result.status = Status.OK
                    log.printer.log_intermediate_result(self.program_name, str(self.result.status) + '(Refinement failed)', str(self.result.verdict))
                    return

                self.current_precision = new_precision


            else: # Should be TRUE or TIMEOUT, already handled. Or UNKNOWN from CPAAlgorithm.
                log.printer.log_debug(5, f"[CEGAR Driver WARN] CPAAlgorithm returned unexpected status/verdict: {iteration_result.status}/{iteration_result.verdict}. Treating as UNKNOWN.")
                self.result.status = Status.ERROR
                self.result.verdict = Verdict.UNKNOWN
                log.printer.log_intermediate_result(self.program_name, str(self.result.status), str(self.result.verdict) + '(CPA Error)')
                return

        # Max refinements reached
        log.printer.log_debug(5, f"[CEGAR Driver WARN] Maximum number of refinements ({self.max_refinements}) reached.")
        self.result.verdict = Verdict.UNKNOWN
        self.result.status = Status.TIMEOUT # Or a specific status for max refinements
        log.printer.log_intermediate_result(self.program_name, str(self.result.status) + '(Max refinements reached)', str(self.result.verdict))
