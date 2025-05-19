#!/usr/bin/env python3
# pycpa/cpaalgorithm.py
"""
Work-list exploration algorithm with early error detection.

Changes
-------
1.  Accept an optional *max_iterations* argument for backward
    compatibility with the old call-site that passed a third positional
    parameter.
2.  Detect *target* states on-the-fly.  A state is a target iff it (or
    any wrapped sub-state) implements ``is_target()`` and that method
    returns *True*.  Hitting a target terminates the search immediately
    with ``Status.ERROR`` so the surrounding CEGAR loop can report
    “FALSE”.
3.  Fixed a long-standing bug where the merge operator was invoked with
    the wrong argument order (it has to merge the *candidate successor*
    into a reached state).
"""

from pycpa.task import Status


class CPAAlgorithm:
    def __init__(self, cpa, task, result, specifications=None):
        self.cpa            = cpa
        self.task           = task
        self.result         = result
        self.specifications = specifications or []
        self.iterations     = 0

    # ------------------------------------------------------------ #
    # helpers                                                      #
    # ------------------------------------------------------------ #
    @staticmethod
    def _is_target(state):
        """Return True iff *state* (or any wrapped sub-state) is a target."""
        return hasattr(state, "is_target") and state.is_target()

    # ------------------------------------------------------------ #
    # main work-list loop                                          #
    # ------------------------------------------------------------ #
    def run(self, reached, waitlist, max_iterations=None):
        """
        Standard work-list exploration with *merge-sep* / *stop-sep*.

        Stops with:
            • Status.ERROR   – a target state has been reached
            • Status.TIMEOUT – iteration budget exhausted
            • Status.OK      – fix-point reached without errors
        """
        budget = max_iterations or self.task.max_iterations

        while waitlist:
            e = waitlist.pop()

            # 1) early error detection on the current state
            if self._is_target(e):
                self.result.status = Status.ERROR
                return

            # 2) budget check
            self.iterations += 1
            if budget and self.iterations >= budget:
                self.result.status = Status.TIMEOUT
                return

            # 3) explore successors
            for succ in self.cpa.get_transfer_relation().get_abstract_successors(e):

                # 3a) early error detection on the successor
                if self._is_target(succ):
                    self.result.status = Status.ERROR
                    return

                to_add, to_remove = set(), set()

                # 3b) merge-sep
                for reached_state in reached:
                    merged = self.cpa.get_merge_operator().merge(succ, reached_state)
                    if merged != reached_state:
                        to_remove.add(reached_state)
                        to_add.add(merged)

                # 3c) stop-sep
                if not self.cpa.get_stop_operator().stop(succ, reached):
                    to_add.add(succ)

                # 3d) maintain the two work sets
                reached -= to_remove
                waitlist -= to_remove
                reached |= to_add
                waitlist |= to_add

        # 4) fix-point reached, no error seen
        self.result.status = Status.OK
