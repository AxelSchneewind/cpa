#!/usr/bin/env python

from pycpa.cfa import CFAEdge

# ## 2. Introducing CPAs (7 tasks, 72 points)
# 
# Now that we managed to create CFAs from our programs, it is time to build the basis for verification.
# As we learned, a flexible way to describe data-flow analysis and model checking is
# using the concept of Configurable Program Analysis (CPA).
# The basic interface of CPA is given below:

# In[12]:


from typing import Collection


class AbstractState(object):
    pass

class WrappedAbstractState(AbstractState):
    @staticmethod
    def unwrap_fully(state) -> Collection[AbstractState]:
        result = []

        for s in WrappedAbstractState.unwrap(state):
            for sub in WrappedAbstractState.unwrap(s):
                result.append(sub)
        return result

    @staticmethod
    def unwrap(state) -> Collection[AbstractState]:
        if hasattr(state, 'wrapped_state'):
            return [ state.wrapped_state ]
        elif hasattr(state, 'wrapped_states'):
            return list(state.wrapped_states)
        elif hasattr(state, 'wrapped'):
            return state.wrapped()
        else:
            return [state]

    @staticmethod
    def get_substate(state : AbstractState, state_type : type) -> AbstractState:
        result = []

        waitlist = list()
        waitlist.append(state)

        while len(waitlist) > 0:
            s = waitlist.pop()

            if isinstance(s, state_type):
                return s

            successors = WrappedAbstractState.unwrap(s)
            for S in successors:
                if s is not S:
                    waitlist.append(S)
        
        assert False, (state, state_type)

    @staticmethod
    def get_substates(state : AbstractState, state_type : type) -> Collection[AbstractState]:
        result = []

        waitlist = list()
        waitlist.append(state)

        while len(waitlist) > 0:
            s = waitlist.pop()

            if isinstance(s, state_type):
                result.append(s)

            successors = WrappedAbstractState.unwrap(s)
            for S in successors:
                if s is not S:
                    waitlist.append(S)
        
        return result

 

class TransferRelation:
    def get_abstract_successors(self, predecessor: AbstractState) -> Collection[AbstractState]:
        raise NotImplementedError("get_abstract_successors not implemented!")

    def get_abstract_successors_for_edge(self, predecessor: AbstractState, edge: CFAEdge) -> Collection[AbstractState]:
        raise NotImplementedError("get_abstract_successors_for_edge not implemented!")

class WrappedTransferRelation(TransferRelation):
    @staticmethod
    def unwrap_fully(rel) -> Collection[TransferRelation]:
        result = []

        for s in WrappedTransferRelation.unwrap(rel):
            for sub in WrappedTransferRelation.unwrap(s):
                result.append(sub)
        return result

    @staticmethod
    def unwrap(rel) -> Collection[TransferRelation]:
        if hasattr(rel, 'wrapped_transfer_relations'):
            return rel.wrapped_transfer_relations
        elif hasattr(rel, 'wrapped_transfer_relation'):
            return [ rel.wrapped_transfer_relation ]
        elif hasattr(rel, 'wrapped'):
            return rel.wrapped()
        else:
            return [rel]

    @staticmethod
    def get_subrelations(rel : TransferRelation, rel_type : type) -> Collection[TransferRelation]:
        result = []

        waitlist = list()
        waitlist.append(rel)

        while len(waitlist) > 0:
            s = waitlist.pop()

            if isinstance(s, rel_type):
                result.append(s)

            successors = WrappedTransferRelation.unwrap(s)
            for S in successors:
                if s is not S:
                    waitlist.append(S)
        
        return result

 


class StopOperator:
    def stop(self, state: AbstractState, reached: Collection[AbstractState]) -> bool:
        raise NotImplementedError("stop not implemented!")


class MergeOperator:
    def merge(self, state1: AbstractState, state2: AbstractState) -> AbstractState:
        raise NotImplementedError("merge not implemented!")


class CPA:
    def get_initial_state(self) -> AbstractState:
        raise NotImplementedError("get_initial_state not implemented!")

    def get_transfer_relation(self) -> TransferRelation:
        raise NotImplementedError("get_transfer_relation not implemented!")

    def get_merge_operator(self) -> MergeOperator:
        raise NotImplementedError("get_merge_operator not implemented!")

    def get_stop_operator(self) -> StopOperator:
        raise NotImplementedError("get_stop_operator not implemented!")



# #### Task 10: Implementing the merge-join operators (3 points)
# 
# Please implement a different merge operator that joins the `ValueState`s instead of the currently used `MergeSepOperator`.

# In[32]:


class MergeJoinOperator(MergeOperator):
    def merge(self, e: AbstractState, eprime: AbstractState) -> AbstractState:
        # TODO
        return eprime




# In `TransferRelation`, we have
# - $e \rightsquigarrow e'$ as `get_abstract_successors(self, predecessor)` and
# - $e \stackrel{g}{\rightsquigarrow} e'$ as `get_abstract_successors_for_edge(self, predecessor, edge)`,
#   where $g$ corresponds to the `CFAEdge` named `edge`.
# 
# #### Task 4: Merge-Sep and Stop-Sep Operators (6 points)
# 
# Please define the merge-sep and stop-sep operators according to what we have learned in the class:

# In[13]:


class MergeSepOperator(MergeOperator):
    def merge(self, e: AbstractState, eprime: AbstractState) -> AbstractState:
        return eprime


class StopSepOperator(StopOperator):
    def __init__(self, subsumes):
        self.subsumes = subsumes

    def stop(self, state: AbstractState, reached: Collection[AbstractState]) -> bool:
        return any((self.subsumes(state, reached_state) for reached_state in reached))



