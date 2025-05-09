#!/usr/bin/env python

# In order to construct an ARG, we need to define an algorithm to explore the state space.
# 
# #### Task 6: Implementing a model-checking algorithm to construct ARGs (10 points)
# 
# Please refer to the pseudo-code in the slides of Week 3.
# Your solution should use a `reached` set and a `waitlist`.

# In[17]:


class MCAlgorithm:
    def __init__(self, cpa):
        self.cpa = cpa

    # DONE Task 6
    def run(self, reached, waitlist):
        while len(waitlist) > 0:
            e = waitlist.pop()
            for e_prime in self.cpa.get_transfer_relation().get_abstract_successors(e):
                if not self.cpa.get_stop_operator().stop(e_prime, reached):
                    reached |= {e_prime}
                    waitlist |= {e_prime}
        return

