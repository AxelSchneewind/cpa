#!/usr/bin/env python

from pycpa.cfa import CFAEdge

from typing import Collection, Generic, TypeVar, Type

class AbstractState(object):
    pass

T = TypeVar('T', bound=AbstractState)


class WrappedAbstractState(AbstractState):
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
    def get_substate(state : AbstractState, state_type : Type[T]) -> T:
        waitlist : list[AbstractState] = list()
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
    def get_substates(state : AbstractState, state_type : Type[T]) -> Collection[T]:
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

 

class TransferRelation(Generic[T]):
    def get_abstract_successors(self, predecessor: T) -> Collection[T]:
        raise NotImplementedError("get_abstract_successors not implemented!")

    def get_abstract_successors_for_edge(self, predecessor: T, edge: CFAEdge) -> Collection[T]:
        raise NotImplementedError("get_abstract_successors_for_edge not implemented!")

class StopOperator(Generic[T]):
    def stop(self, state: T, reached: Collection[T]) -> bool:
        raise NotImplementedError("stop not implemented!")


class MergeOperator(Generic[T]):
    def merge(self, state1: T, state2: T) -> AbstractState:
        raise NotImplementedError("merge not implemented!")


class CPA(Generic[T]):
    def get_initial_state(self) -> T:
        raise NotImplementedError("get_initial_state not implemented!")

    def get_transfer_relation(self) -> TransferRelation[T]:
        raise NotImplementedError("get_transfer_relation not implemented!")

    def get_merge_operator(self) -> MergeOperator[T]:
        raise NotImplementedError("get_merge_operator not implemented!")

    def get_stop_operator(self) -> StopOperator[T]:
        raise NotImplementedError("get_stop_operator not implemented!")


class MergeSepOperator(MergeOperator[T]):
    def merge(self, e: T, eprime: T) -> T:
        return eprime


class StopSepOperator(StopOperator[T]):
    def __init__(self, subsumes):
        self.subsumes = subsumes

    def stop(self, state: T, reached: Collection[T]) -> bool:
        return any((self.subsumes(state, reached_state) for reached_state in reached))



