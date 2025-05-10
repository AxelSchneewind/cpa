#!/usr/bin/env python

# #### Task 7: Implementing the CPA algorithm (15 points)
# 
# To have a configurable way to explore the state space,
# let's extend the model-checking algorithm to the CPA algorithm.

# In[20]:



class CPAAlgorithm:
    def __init__(self, cpa):
        self.cpa = cpa
        self.iterations = 0

    def run(self, reached, waitlist):
        while len(waitlist) > 0 and self.iterations < 100:
            e = waitlist.pop()
            self.iterations += 1

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

                reached -= to_remove
                reached |= to_add
                waitlist -= to_remove
                waitlist |= to_add

        return

