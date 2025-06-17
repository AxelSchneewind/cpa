#!/usr/bin/env python3
"""
Predicate Abstraction + Precision object + SSA helpers.
Stores predicates globally and per-CFA-node.
"""

import ast
import hashlib
from typing import Dict, Iterable, Set, List, Optional

from pysmt.shortcuts import (
    And, Or, Not, Equals, NotEquals, Symbol,
    substitute, get_env
)
from pysmt.typing import BV64
from pysmt.fnode import FNode

from pycpa.cfa import InstructionType, CFAEdge, CFANode # Assuming CFANode is hashable

from pycpa import log

import copy

# ------------------ #
#  SSA helpers       #
# ------------------ #
class SSA:
    @staticmethod   
    def is_ssa(var: str | FNode) -> FNode:
        name_parts = var.symbol_name().split('#') if isinstance(var, FNode) else var.split('#')
        return len(name_parts) == 2

    @staticmethod   
    def ssa(var: str, idx: int) -> FNode:
        assert not '#' in var, f"Variable name '{var}' should not contain '#'"
        return Symbol(f"{var}#{idx}", BV64)
    
    @staticmethod   
    def next(var: str, idx: dict[str, int]) -> int:
        idx[var] = idx.get(var, 0) + 1
        return idx[var]
    
    @staticmethod   
    def get_name(symbol : FNode) -> str:
        name_parts = symbol.symbol_name().split('#')
        return name_parts[0]
    
    @staticmethod   
    def get_idx(symbol : FNode) -> Optional[int]:
        name_parts = symbol.symbol_name().split('#')
        return int(name_parts[-1]) if len(name_parts) > 1 else 0
    
    @staticmethod   
    def inc_index(symbol : FNode, increment : int) -> FNode:
        name = SSA.get_name(symbol)
        current_idx = SSA.get_idx(symbol)
        current_idx = current_idx if current_idx is not None else 0
        return SSA.ssa(name, current_idx + increment)
    
    @staticmethod   
    def set_index(symbol : FNode, idx : int) -> FNode:
        name = SSA.get_name(symbol)
        return SSA.ssa(name, idx)
    
    
    @staticmethod   
    def unindex_symbol(symbol: FNode) -> FNode:
        """Returns a symbol with the SSA index removed"""
        assert symbol.is_symbol(), symbol
        name = SSA.get_name(symbol)
        return Symbol(name, symbol.symbol_type())
    
    @staticmethod   
    def unindex_predicate(predicate: FNode) -> FNode:
        """
        Replaces all SSA-indexed variables in a predicate with their unindexed versions.
        e.g., (x#1 > y#0) becomes (x > y)
        """
        substitution_targets = [
            sub
            for sub in get_env().formula_manager.get_all_symbols()
        ]

        substitution = {
            var_symbol : SSA.unindex_symbol(var_symbol)
            for var_symbol in substitution_targets
        }

        assert all(not SSA.is_ssa(sub) for _,sub in substitution.items())
        return substitute(predicate, substitution)
    
    
    @staticmethod   
    def inc_indices(formula : FNode, indices : int | dict[str,int]) -> FNode:
        substitution_targets = [
            sub
            for sub in get_env().formula_manager.get_all_symbols()
        ]
        
        substitution = {}
        if isinstance(indices, int):
            substitution = {
                target : SSA.inc_index(target, indices)
                for target in substitution_targets
            }
        else:
            assert isinstance(indices, dict)
            substitution = {
                target : SSA.inc_index(target, indices[SSA.get_name(target)]) 
                for target in substitution_targets
                if SSA.get_name(target) in indices # Ensure key exists
            }
        
        assert all(SSA.is_ssa(sub) for _,sub in substitution.items())
        return substitute(formula, substitution)
    
    
    @staticmethod   
    def set_indices(formula : FNode, indices : int | dict[str,int]) -> FNode:
        substitution_targets = [
            sub
            for sub in get_env().formula_manager.get_all_symbols()
        ]
        
        substitution = {}
        if isinstance(indices, int):
            substitution = {
                target : SSA.set_index(target, indices) 
                for target in substitution_targets
            }
        else:
            assert isinstance(indices, dict)
            substitution = {
                target : SSA.set_index(target, indices.get(SSA.get_name(target), 0)) 
                for target in substitution_targets
            }
        
        assert all(SSA.is_ssa(sub) for _,sub in substitution.items())
        return substitute(formula, substitution)
    
    @staticmethod   
    def pad_indices(formula : FNode, indices : dict[str,int], target_indices : dict[str,int]):
        """ 
        Adds padding assignments to the given formula such that for a variable x, its index becomes max(indices[x], target_indices[x])
        """
        padding_terms = []
        for sub in get_env().formula_manager.get_all_symbols():
            name = SSA.get_name(sub)
            if name not in indices or name not in target_indices:
                continue
            if indices[name] >= target_indices[name]:
                continue

            term = Equals(
                    SSA.ssa(name, target_indices[name]),
                    SSA.ssa(name, indices[name])
            )
            padding_terms.append(term)
    
        return And(formula, And(padding_terms))


