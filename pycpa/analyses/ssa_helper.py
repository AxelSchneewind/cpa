#!/usr/bin/env python3
"""
Predicate Abstraction + Precision object + SSA helpers.
Stores predicates globally and per-CFA-node.
"""

import ast
import hashlib
from typing import Dict, Iterable, Set, List, Optional

from pysmt.shortcuts import (
    And, Or, Not, Equals, NotEquals,
    BV, Symbol, TRUE, FALSE, Ite,
    BVNot, BVNeg, BVSGT, BVSGE, BVSLT, BVSLE,
    BVAdd, BVMul, BVSDiv, BVURem, # Changed BVSDiv twice to BVSDiv, BVURem
    BVLShl, BVAShr, BVOr, BVXor, BVAnd,
    substitute, get_env
)
from pysmt.typing import BV64, BOOL
from pysmt.fnode import FNode

from pycpa.cfa import InstructionType, CFAEdge, CFANode # Assuming CFANode is hashable

from pycpa import log

import copy

# ------------------ #
#  SSA helpers       #
# ------------------ #
class SSA:
    @staticmethod   
    def ssa(var: str, idx: int) -> FNode:
        assert not '#' in var, f"Variable name '{var}' should not contain '#'"
        return Symbol(f"{var}#{idx}", BV64)
    
    @staticmethod   
    def next(var: str, idx: Dict[str, int]) -> int:
        idx[var] = idx.get(var, 0) + 1
        return idx[var]
    
    @staticmethod   
    def get_name(symbol : FNode) -> str:
        name_parts = symbol.symbol_name().split('#')
        return name_parts[0]
    
    @staticmethod   
    def get_idx(symbol : FNode) -> Optional[int]:
        name_parts = symbol.symbol_name().split('#')
        if len(name_parts) > 1:
            try:
                return int(name_parts[-1])
            except ValueError:
                # If the part after # is not an int, it's not an SSA index we manage this way
                return None
        return None
    
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
        """Returns a symbol with the SSA index removed, or the original if no index."""
        if symbol.is_symbol():
            name = SSA.get_name(symbol)
            return Symbol(name, symbol.symbol_type())
        return symbol # Should ideally only be called on symbols
    
    @staticmethod   
    def unindex_predicate(predicate: FNode) -> FNode:
        """
        Replaces all SSA-indexed variables in a predicate with their unindexed versions.
        e.g., (x#1 > y#0) becomes (x > y)
        """
        if not predicate.get_free_variables():
            return predicate
    
        substitution = {}
        for var_symbol in predicate.get_free_variables():
            unindexed_var = SSA.unindex_symbol(var_symbol)
            if var_symbol != unindexed_var: # only add to substitution if it changed
                substitution[var_symbol] = unindexed_var
                
        if not substitution:
            return predicate
            
        return predicate.substitute(substitution)
    
    
    @staticmethod   
    def inc_indices(formula : FNode, indices : int | dict[str,int]) -> FNode:
        # log.printer.log_debug(5, f"[PredAbsPrecision DEBUG] inc_indices: formula={formula}, indices={indices}")
        substitution_targets = []
        for sub in get_env().formula_manager.get_all_symbols():
            if sub.is_symbol():
                if isinstance(indices, dict) and SSA.get_name(sub) not in indices:
                    continue
                substitution_targets.append(sub)
        
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
        
        return substitute(formula, substitution)
    
    
    
    @staticmethod   
    def set_indices(formula : FNode, indices : int | dict[str,int]) -> FNode:
        # log.printer.log_debug(5, f"[PredAbsPrecision DEBUG] set_indices: formula={formula}, indices={indices}")
        substitution_targets = []
        for sub in get_env().formula_manager.get_all_symbols():
            if sub.is_symbol():
                if isinstance(indices, dict) and SSA.get_name(sub) not in indices:
                    continue
                substitution_targets.append(sub)
        
        substitution = {}
        if isinstance(indices, int):
            substitution = {
                target : SSA.set_index(target, indices) 
                for target in substitution_targets
            }
        else:
            assert isinstance(indices, dict)
            substitution = {
                target : SSA.set_index(target, indices[SSA.get_name(target)]) 
                for target in substitution_targets
                if SSA.get_name(target) in indices # Ensure key exists
            }
        
        return substitute(copy.copy(formula), substitution)
    
    @staticmethod   
    def pad_indices(formula : FNode, indices : dict[str,int], target_indices : dict[str,int]):
        padding_terms = []
        for sub in get_env().formula_manager.get_all_symbols():
            if sub.is_symbol():
                name = SSA.get_name(sub)
                if name not in indices or name not in target_indices:
                    continue
                term = Equals(
                        SSA.ssa(name, target_indices[name]),
                        SSA.ssa(name, indices[name])
                )
                padding_terms.append(term)
    
        return And(formula, And(padding_terms))


