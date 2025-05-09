#!/bin/env/python

from pycpa import CPA
from pycpa import CFA

from typing import Collection

# ### LocationCPA
# 
# We will implement a CPA $\mathbb{L}$ that tracks the current location in the program,
# which is called *LocationCPA*.
# 
# #### Task 5: Implementing transfer relation and stop operator of LocationCPA (6 points)
# 
# We will implement the transfer relation, which returns the successor location,
# and the stop operator, which returns true if a location has been explored in the reached set.
# (Note that, for the merge operator, we use the default merge-sep operator implemented above.)

# In[14]:


class LocationState(CPA.AbstractState):
    def __init__(self, node: CFA.CFANode):
        self.location = node

    def __str__(self):
        return "@%s" % self.location.node_id

    def __eq__(self, other):
        return self.location == other.location

    def __hash__(self):
        return self.location.__hash__()


class LocationTransferRelation(CPA.TransferRelation):

    def get_abstract_successors(self, predecessor: LocationState) -> Collection[LocationState]:
        return [LocationState(edge.successor) for edge in predecessor.location.leaving_edges]

    def get_abstract_successors_for_edge(self, predecessor: LocationState, edge: CFA.CFAEdge) -> Collection[LocationState]:
        return [LocationState(edge.successor)]


class LocationStopOperator(CPA.StopSepOperator):
    def __init__(self):
        return CPA.StopSepOperator.__init__(self, LocationState.__eq__)


class LocationCPA(CPA.CPA):
    def __init__(self, cfa_root: CFA.CFANode):
        self.root = cfa_root

    def get_initial_state(self):
        return LocationState(self.root)

    def get_stop_operator(self):
        return LocationStopOperator()

    def get_merge_operator(self):
        return MergeSepOperator()

    def get_transfer_relation(self):
        return LocationTransferRelation()



