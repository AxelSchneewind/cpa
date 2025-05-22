#!/usr/bin/env python

from pycpa.cpa import CPA, AbstractState, TransferRelation, MergeOperator, StopOperator, MergeSepOperator
from pycpa.cfa import InstructionType, CFAEdge

import ast

# ### PropertyCPA
# 
# In this part, we will write a CPA that checks for whether the function `reach_error` has been invoked on the explored path.
# The `__str__` method of the states of that CPA should mark each state as either `unsafe` or `safe`
# depending on whether this call has been reached or not.
# (You are on your own here, we will not give you any code to start with.
# You might want to create a visitor that checks for call nodes in the instructions and use that one in your transfer relation.)
# 
# #### Task 9: Implementing PropertyCPA (10 points)

# In[28]:


class PropertyState(AbstractState):
    def __init__(self, is_safe):
        self.safe = is_safe

    def subsumes(self, other):
        return other.safe == None or self.safe == other.safe

    def __eq__(self, other):
        return self.safe == other.safe

    def __hash__(self):
        return self.safe.__hash__()

    def __str__(self):
        if self.safe:
            return 'safe'
        else:
            return 'unsafe'


class PropertyTransferRelation(TransferRelation):
    def get_abstract_successors(self, predecessor : PropertyState):
        raise NotImplementedError(
            "successors without edge not possible for Property Analysis!"
        )

    def get_abstract_successors_for_edge(self, predecessor : PropertyState, edge : CFAEdge):
        kind = edge.instruction.kind
        if kind == InstructionType.REACH_ERROR:
            return [PropertyState(False)]
        else:
            return [predecessor]


class PropertyStopOperator(StopOperator):
    def stop(self, e, reached):
        return not e.safe


class PropertyCPA(CPA):
    def get_initial_state(self):
        return PropertyState(True)

    def get_stop_operator(self):
        return PropertyStopOperator()

    def get_merge_operator(self):
        # simply use merge sep
        return MergeSepOperator()

    def get_transfer_relation(self):
        return PropertyTransferRelation()


