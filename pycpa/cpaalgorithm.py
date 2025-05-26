#!/usr/bin/env python

# #### Task 7: Implementing the CPA algorithm (15 points)
# 
# To have a configurable way to explore the state space,
# let's extend the model-checking algorithm to the CPA algorithm.

# In[20]:


from pycpa.task import Task, Result, Status
from pycpa.cpa import WrappedAbstractState
from pycpa.analyses import PropertyState
from pycpa.verdict import Verdict


class CPAAlgorithm:
    def __init__(self, cpa, specifications, task : Task, result : Result):
        self.cpa = cpa
        self.iterations = 0
        self.task = task
        self.result = result

    def run(self, entry):
        waitlist = set()
        reached = set()
        waitlist.add(entry)
        reached.add(entry)

        while len(waitlist) > 0:
            e = waitlist.pop()

            self.iterations += 1
            if self.task.max_iterations and self.iterations >= self.task.max_iterations:
                self.result.status = Status.TIMEOUT
                self.result.verdict = Verdict.UNKNOWN  # cannot get better than unknown
                return

            for e_prime in self.cpa.get_transfer_relation().get_abstract_successors(e):
                # store states that have to be added/removed from the sets here, to prevent modification during iteration
                to_add = set()
                to_remove = set()

                for e_reached in reached:
                    e_merged =  self.cpa.get_merge_operator().merge(e, e_reached)
                    if e_merged != e_reached:
                        to_add.add(e_merged)
                        to_remove.add(e_reached)

                if not self.cpa.get_stop_operator().stop(e_prime, reached):
                    to_add.add(e_prime)

                if any(not s.safe for s in WrappedAbstractState.get_substates(e, PropertyState)):
                    self.result.status = Status.OK
                    self.result.verdict = Verdict.FALSE
                    self.result.witness = e
                    break

                reached -= to_remove
                reached |= to_add
                waitlist -= to_remove
                waitlist |= to_add

        self.result.status = Status.OK
        self.result.verdict = Verdict.TRUE
        return

