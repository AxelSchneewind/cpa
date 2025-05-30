#!/usr/bin/env python3
"""
Predicate Abstraction + Precision object + SSA helpers.
Stores predicates globally and per-CFA-node.
"""

from __future__ import annotations
import ast
import hashlib
from typing import Dict, Iterable, Set, List, Optional

from pysmt.shortcuts import (
    And, Or, Not, Equals, NotEquals,
    BV, Symbol, TRUE, FALSE, Ite,
    BVNot, BVNeg, BVSGT, BVSGE, BVSLT, BVSLE,
    BVAdd, BVMul, BVSDiv, BVURem, # Changed BVSDiv twice to BVSDiv, BVURem
    BVLShl, BVAShr, BVOr, BVXor, BVAnd
)
from pysmt.typing import BV64, BOOL
from pysmt.fnode import FNode

from pycpa.cfa import InstructionType, CFAEdge, CFANode # Assuming CFANode is hashable

from pycpa import log

# ------------------ #
#  SSA helpers       #
# ------------------ #
def _ssa(var: str, idx: int) -> FNode:
    assert not '#' in var, f"Variable name '{var}' should not contain '#'"
    return Symbol(f"{var}#{idx}", BV64)

def _next(var: str, ssa: Dict[str, int]) -> int:
    ssa[var] = ssa.get(var, 0) + 1
    return ssa[var]

def _ssa_get_name(symbol : FNode) -> str:
    name_parts = symbol.symbol_name().split('#')
    assert len(name_parts) >= 1, f"Symbol name '{symbol.symbol_name()}' does not follow expected SSA pattern."
    return name_parts[0]

def _ssa_get_idx(symbol : FNode) -> Optional[int]:
    name_parts = symbol.symbol_name().split('#')
    if len(name_parts) > 1:
        try:
            return int(name_parts[-1])
        except ValueError:
            # If the part after # is not an int, it's not an SSA index we manage this way
            return None
    return None

def _ssa_inc_index(symbol : FNode, increment : int) -> FNode:
    name = _ssa_get_name(symbol)
    current_idx = _ssa_get_idx(symbol)
    # If there's no current index, or it's not what we expect, how to handle?
    # For now, assume if an index exists, it's the one to increment.
    # This might need refinement if variables can have '#' in their non-SSA names.
    new_idx = (current_idx + increment) if current_idx is not None else increment
    return _ssa(name, new_idx)

def _ssa_set_index(symbol : FNode, idx : int) -> FNode:
    name = _ssa_get_name(symbol)
    return _ssa(name, idx)

def unindex_symbol(symbol: FNode) -> FNode:
    """Returns a symbol with the SSA index removed, or the original if no index."""
    if symbol.is_symbol():
        name = _ssa_get_name(symbol)
        return Symbol(name, symbol.symbol_type())
    return symbol # Should ideally only be called on symbols

def unindex_predicate(predicate: FNode) -> FNode:
    """
    Replaces all SSA-indexed variables in a predicate with their unindexed versions.
    e.g., (x#1 > y#0) becomes (x > y)
    """
    if not predicate.get_free_variables():
        return predicate

    substitution = {}
    for var_symbol in predicate.get_free_variables():
        unindexed_var = unindex_symbol(var_symbol)
        if var_symbol != unindexed_var: # only add to substitution if it changed
            substitution[var_symbol] = unindexed_var
            
    if not substitution:
        return predicate
        
    return predicate.substitute(substitution)


# --------------------------------- #
#  Expression → SMT                 #
# --------------------------------- #
def _cast(formula : FNode, target_type):
    actual_type = formula.get_type()
    if actual_type == target_type:
        return formula
    if target_type.is_bv_type() and actual_type.is_bool_type():
        return Ite(formula, BV(1, 64), BV(0, 64))
    if target_type.is_bool_type() and actual_type.is_bv_type():
        return NotEquals(formula, BV(0, 64))
    log.printer.log_debug(1, f"[PredAbsPrecision DEBUG] _cast: Cannot cast from {actual_type} to {target_type} for formula {formula}")
    return formula


def _bool(t: FNode) -> FNode:
    return _cast(t, BOOL)

def _bv(t: FNode) -> FNode:
    return _cast(t, BV64)


def _expr2smt(node: ast.AST, ssa: Dict[str, int]) -> FNode:
    log.printer.log_debug(5, f"[PredAbsPrecision DEBUG] _expr2smt visiting: {ast.dump(node)} with ssa {ssa}")
    match node:
        case ast.Name(id=v):
            return _ssa(v, ssa.get(v, 0))

        case ast.Constant(value=v):
            if isinstance(v, bool): return TRUE() if v else FALSE()
            if isinstance(v, int):  return BV(v, 64)
            h = hashlib.md5(repr(v).encode()).hexdigest()[:8]
            log.printer.log_debug(1, f"[PredAbsPrecision WARN] _expr2smt: Unknown constant type {type(v)}, creating symbolic const_{h}")
            return _ssa(f"const_{h}", 0) # Fallback for other const types

        case ast.BinOp(left=l, op=op_type, right=r): # Consolidate BinOp
            left_smt = _expr2smt(l, ssa)
            right_smt = _expr2smt(r, ssa)

            # Ensure consistent types for arithmetic ops, cast if necessary
            if not isinstance(op_type, (ast.Eq, ast.NotEq, ast.And, ast.Or)): # Non-boolean binary ops
                 # Attempt to cast to BV64 if not already, common for arithmetic
                if left_smt.get_type() != BV64: left_smt = _bv(left_smt)
                if right_smt.get_type() != BV64: right_smt = _bv(right_smt)

            if isinstance(op_type, ast.Add):  return BVAdd(left_smt, right_smt)
            if isinstance(op_type, ast.Sub):  return BVAdd(left_smt, BVNeg(right_smt)) # Or BVSub
            if isinstance(op_type, ast.Mult): return BVMul(left_smt, right_smt)
            if isinstance(op_type, ast.Div):  return BVSDiv(left_smt, right_smt)
            if isinstance(op_type, ast.FloorDiv): return BVSDiv(left_smt, right_smt) # Same for SMT
            if isinstance(op_type, ast.Mod):  return BVURem(left_smt, right_smt)
            # Pow not directly supported by SMT-LIB standard for BVs easily, placeholder
            if isinstance(op_type, ast.Pow):  
                log.printer.log_debug(1, f"[PredAbsPrecision WARN] _expr2smt: Operator ast.Pow not directly supported, returning TRUE.")
                return TRUE()


            if isinstance(op_type, ast.BitAnd): return BVAnd(left_smt, right_smt)
            if isinstance(op_type, ast.BitOr):  return BVOr(left_smt, right_smt)
            if isinstance(op_type, ast.BitXor): return BVXor(left_smt, right_smt)
            if isinstance(op_type, ast.LShift): return BVLShl(left_smt, right_smt)
            if isinstance(op_type, ast.RShift): return BVAShr(left_smt, right_smt) # Arithmetic shift

            # Equality can compare different types in Python, SMT is stricter
            if isinstance(op_type, ast.Eq):
                # Attempt to make types compatible for Equals
                if left_smt.get_type() != right_smt.get_type():
                    # Simple heuristic: if one is bool, try to make other bool
                    if left_smt.get_type() == BOOL: right_smt = _bool(right_smt)
                    elif right_smt.get_type() == BOOL: left_smt = _bool(left_smt)
                    # Add more casting logic if needed, or rely on _cast to handle common cases
                return Equals(left_smt, right_smt)
            if isinstance(op_type, ast.NotEq):
                if left_smt.get_type() != right_smt.get_type():
                    if left_smt.get_type() == BOOL: right_smt = _bool(right_smt)
                    elif right_smt.get_type() == BOOL: left_smt = _bool(left_smt)
                return NotEquals(left_smt, right_smt)
            
            log.printer.log_debug(1, f"[PredAbsPrecision WARN] _expr2smt: Unhandled BinOp operator {type(op_type)}, returning TRUE.")
            return TRUE()


        case ast.BoolOp(op=op_type, values=vs):
            smt_values = [_bool(_expr2smt(v, ssa)) for v in vs]
            if isinstance(op_type, ast.And): return And(smt_values)
            if isinstance(op_type, ast.Or):  return Or(smt_values)
            log.printer.log_debug(1, f"[PredAbsPrecision WARN] _expr2smt: Unhandled BoolOp operator {type(op_type)}, returning TRUE.")
            return TRUE()

        case ast.UnaryOp(op=op_type, operand=o):
            smt_operand = _expr2smt(o, ssa)
            if isinstance(op_type, ast.Not):  return Not(_bool(smt_operand))
            if isinstance(op_type, ast.USub): return BVNeg(_bv(smt_operand))
            if isinstance(op_type, ast.UAdd): return _bv(smt_operand) # UAdd is identity
            if isinstance(op_type, ast.Invert): return BVNot(_bv(smt_operand)) # Bitwise NOT
            log.printer.log_debug(1, f"[PredAbsPrecision WARN] _expr2smt: Unhandled UnaryOp operator {type(op_type)}, returning TRUE.")
            return TRUE()

        case ast.Compare(left=l, ops=ops, comparators=comps):
            # SMT-LIB Compare is binary, Python's can be chained (e.g. a < b < c)
            # We handle the common case of a single comparison first.
            # For chained comparisons, we'd need to break them into (a < b) AND (b < c).
            if len(ops) == 1:
                lhs = _expr2smt(l, ssa)
                rhs = _expr2smt(comps[0], ssa)
                op_type = ops[0]

                # Ensure operands are compatible, typically numeric (BV) for comparisons
                if lhs.get_type() != BV64: lhs = _bv(lhs)
                if rhs.get_type() != BV64: rhs = _bv(rhs)

                if isinstance(op_type, ast.Lt):  return BVSLT(lhs, rhs)
                if isinstance(op_type, ast.LtE): return BVSLE(lhs, rhs)
                if isinstance(op_type, ast.Gt):  return BVSGT(lhs, rhs)
                if isinstance(op_type, ast.GtE): return BVSGE(lhs, rhs)
                if isinstance(op_type, ast.Eq):  return Equals(lhs, rhs) # Already handled in BinOp, but can appear here
                if isinstance(op_type, ast.NotEq): return NotEquals(lhs, rhs)
                # Python's 'is', 'is not', 'in', 'not in' are not directly mapped here.
                # For this tool, we assume comparisons are arithmetic/equality.
                log.printer.log_debug(1, f"[PredAbsPrecision WARN] _expr2smt: Unhandled Compare operator {type(op_type)}, returning TRUE.")
                return TRUE()
            else: # Chained comparison: x < y < z  => (x < y) & (y < z)
                conjuncts = []
                current_lhs_ast = l
                for i in range(len(ops)):
                    op_type = ops[i]
                    current_rhs_ast = comps[i]

                    lhs = _expr2smt(current_lhs_ast, ssa)
                    rhs = _expr2smt(current_rhs_ast, ssa)
                    
                    if lhs.get_type() != BV64: lhs = _bv(lhs)
                    if rhs.get_type() != BV64: rhs = _bv(rhs)

                    if isinstance(op_type, ast.Lt):  conjuncts.append(BVSLT(lhs, rhs))
                    elif isinstance(op_type, ast.LtE): conjuncts.append(BVSLE(lhs, rhs))
                    elif isinstance(op_type, ast.Gt):  conjuncts.append(BVSGT(lhs, rhs))
                    elif isinstance(op_type, ast.GtE): conjuncts.append(BVSGE(lhs, rhs))
                    elif isinstance(op_type, ast.Eq):  conjuncts.append(Equals(lhs, rhs))
                    elif isinstance(op_type, ast.NotEq): conjuncts.append(NotEquals(lhs, rhs))
                    else:
                        log.printer.log_debug(1, f"[PredAbsPrecision WARN] _expr2smt: Unhandled chained Compare operator {type(op_type)}, adding TRUE.")
                        conjuncts.append(TRUE())
                    current_lhs_ast = current_rhs_ast # For next comparison in chain
                return And(conjuncts)


        case ast.Call(func=ast.Name(id=fname), args=args):
            call_ret_var_name = f"call_{fname}_ret_{len(ssa)}" # Simple unique name
            return _ssa(call_ret_var_name, _next(call_ret_var_name, ssa))


        case _:
            log.printer.log_debug(5, f"[PredAbsPrecision ERROR] _expr2smt: Unsupported AST node type {type(node)}: {ast.dump(node)}. Returning TRUE as fallback.")
            return TRUE()


# --------------------------------------------------------------------------- #
#  Precision object (mapping from CFANode to predicate set)                   #
# --------------------------------------------------------------------------- #
class PredAbsPrecision:
    def __init__(self,
                 global_preds: Optional[Set[FNode]] = None,
                 function_preds: Optional[Dict[str, Set[FNode]]] = None,
                 local_preds: Optional[Dict[CFANode, Set[FNode]]] = None):
        # Store unindexed predicates
        self.global_predicates: Set[FNode] = global_preds if global_preds is not None else set()
        self.function_predicates: Dict[str, Set[FNode]] = function_preds if function_preds is not None else {}
        self.local_predicates: Dict[CFANode, Set[FNode]] = local_preds if local_preds is not None else {}
        log.printer.log_debug(5, f"[PredAbsPrecision INFO] Initialized precision: Global={len(self.global_predicates)}, Function={len(self.function_predicates)}, Local={len(self.local_predicates)}")

    def get_predicates_for_location(self, loc_node: CFANode) -> Set[FNode]:
        """
        Retrieves all applicable predicates for a given CFA node,
        combining global, function-specific, and location-specific predicates.
        """
        log.printer.log_debug(5, f"[PredAbsPrecision DEBUG] Getting predicates for location: {loc_node.node_id if loc_node else 'None'}")
        if loc_node is None: # Should not happen if loc_node is always a CFANode
            return self.global_predicates.copy()

        preds = self.global_predicates.copy()
        log.printer.log_debug(5, f"[PredAbsPrecision DEBUG] Global preds: {preds}")

        func_name = loc_node.get_function_name() # Assuming CFANode has this method
        if func_name and func_name in self.function_predicates:
            preds.update(self.function_predicates[func_name])
            log.printer.log_debug(5, f"[PredAbsPrecision DEBUG] Added function '{func_name}' preds: {self.function_predicates[func_name]}")


        if loc_node in self.local_predicates:
            preds.update(self.local_predicates[loc_node])
            log.printer.log_debug(5, f"[PredAbsPrecision DEBUG] Added local (node {loc_node.node_id}) preds: {self.local_predicates[loc_node]}")
        
        log.printer.log_debug(5, f"[PredAbsPrecision DEBUG] Total preds for node {loc_node.node_id}: {preds}")
        return preds

    def __getitem__(self, loc_node: CFANode) -> Set[FNode]:
        """Allows dictionary-like access, e.g., precision[cfa_node]."""
        return self.get_predicates_for_location(loc_node)

    def add_global_predicates(self, new_preds: Iterable[FNode]):
        """Adds new global predicates. Predicates are unindexed before storing."""
        count_before = len(self.global_predicates)
        for p in new_preds:
            self.global_predicates.add(unindex_predicate(p))
        log.printer.log_debug(5, f"[PredAbsPrecision INFO] Added {len(self.global_predicates) - count_before} new global predicates. Total global: {len(self.global_predicates)}")

    def add_function_predicates(self, func_name: str, new_preds: Iterable[FNode]):
        """Adds new function-specific predicates. Predicates are unindexed."""
        if func_name not in self.function_predicates:
            self.function_predicates[func_name] = set()
        
        count_before = len(self.function_predicates[func_name])
        for p in new_preds:
            self.function_predicates[func_name].add(unindex_predicate(p))
        log.printer.log_debug(5, f"[PredAbsPrecision INFO] Added {len(self.function_predicates[func_name]) - count_before} new preds for function '{func_name}'. Total for func: {len(self.function_predicates[func_name])}")


    def add_local_predicates_map(self, new_local_preds_map: Dict[CFANode, Iterable[FNode]]):
        """Adds new location-specific predicates from a map. Predicates are unindexed."""
        for loc_node, preds_for_loc in new_local_preds_map.items():
            if loc_node not in self.local_predicates:
                self.local_predicates[loc_node] = set()
            
            count_before = len(self.local_predicates[loc_node])
            for p in preds_for_loc:
                self.local_predicates[loc_node].add(unindex_predicate(p))
            added_count = len(self.local_predicates[loc_node]) - count_before
            if added_count > 0:
                 log.printer.log_debug(5, f"[PredAbsPrecision INFO] Added {added_count} new local preds for node {loc_node.node_id}. Total for node: {len(self.local_predicates[loc_node])}")


    def __str__(self) -> str:
        return (f"PredAbsPrecision(Global: {len(self.global_predicates)} preds, "
                f"Function-specific: {sum(len(p) for p in self.function_predicates.values())} across {len(self.function_predicates)} funcs, "
                f"Local: {sum(len(p) for p in self.local_predicates.values())} across {len(self.local_predicates)} locs)")

    @staticmethod
    def ssa_inc_indices(formula : FNode, indices : int | dict[str,int]) -> FNode:
        # log.printer.log_debug(5, f"[PredAbsPrecision DEBUG] ssa_inc_indices: formula={formula}, indices={indices}")
        result = formula
        substitution_targets = []
        for sub in result.get_free_variables():
            if sub.is_symbol():
                if isinstance(indices, dict) and _ssa_get_name(sub) not in indices:
                    continue
                substitution_targets.append(sub)
        
        substitution = {}
        if isinstance(indices, int):
            substitution = {
                target : _ssa_inc_index(target, indices)
                for target in substitution_targets
            }
        else: # isinstance(indices, dict)
            substitution = {
                target : _ssa_set_index(target, indices[_ssa_get_name(target)]) 
                for target in substitution_targets
                if _ssa_get_name(target) in indices # Ensure key exists
            }
        
        if not substitution: return result
        return result.substitute(substitution)


    @staticmethod
    def ssa_set_indices(formula : FNode, indices : int | dict[str,int]) -> FNode:
        # log.printer.log_debug(5, f"[PredAbsPrecision DEBUG] ssa_set_indices: formula={formula}, indices={indices}")
        result = formula
        substitution_targets = []
        for sub in result.get_free_variables():
            if sub.is_symbol():
                if isinstance(indices, dict) and _ssa_get_name(sub) not in indices:
                    continue
                substitution_targets.append(sub)
        
        substitution = {}
        if isinstance(indices, int):
            substitution = {
                target : _ssa_set_index(target, indices) 
                for target in substitution_targets
            }
        else: # isinstance(indices, dict)
            substitution = {
                target : _ssa_set_index(target, indices[_ssa_get_name(target)]) 
                for target in substitution_targets
                if _ssa_get_name(target) in indices # Ensure key exists
            }
        
        if not substitution: return result
        return result.substitute(substitution)

    @staticmethod
    def ssa_from_call(edge: CFAEdge, ssa_indices: Dict[str, int]) -> FNode:
        instr = edge.instruction
        log.printer.log_debug(5, f"[PredAbsPrecision DEBUG] ssa_from_call: edge='{edge.label()}', ssa_indices={ssa_indices}")

        if hasattr(instr, 'target_variable') and instr.target_variable:
            target_var = instr.target_variable

            log.printer.log_debug(5, f"[PredAbsPrecision DEBUG] ssa_from_call: Nondet/Builtin call, advancing SSA for target '{target_var}'")
            _next(target_var, ssa_indices) # Advance SSA for the target variable

        # Handle regular function calls with parameter passing
        if not hasattr(instr, "param_names") or not hasattr(instr, "arg_names"):
            log.printer.log_debug(5, "[PredAbsPrecision DEBUG] ssa_from_call: No param_names or arg_names, returning TRUE.")
            return TRUE()

        conjuncts = []
        # 1. map each actual argument to the formal parameter
        #    formal_new_ssa = actual_current_ssa
        for formal, actual_name_str in zip(instr.param_names, instr.arg_names):
            # actual_name_str might be a variable name or a constant string
            # We need to create an AST node to pass to _expr2smt
            try:
                # If actual_name_str is a number, treat it as a constant
                actual_val = int(actual_name_str)
                actual_ast_node = ast.Constant(value=actual_val)
            except ValueError:
                # Otherwise, treat it as a variable name
                actual_ast_node = ast.Name(id=actual_name_str, ctx=ast.Load())
            
            rhs = _expr2smt(actual_ast_node, ssa_indices) # Use current SSA for actual
            lhs = _ssa(formal, _next(formal, ssa_indices))   # Use next SSA for formal
            conjuncts.append(Equals(lhs, rhs))
            log.printer.log_debug(5, f"[PredAbsPrecision DEBUG] ssa_from_call: Param assignment {lhs} = {rhs}")

        log.printer.log_debug(5, f"[PredAbsPrecision DEBUG] ssa_from_call: conjuncts={conjuncts}")
        return And(conjuncts) if conjuncts else TRUE()


    @staticmethod
    def ssa_from_return(edge: CFAEdge, ssa_indices: Dict[str, int]) -> FNode:
        instr = edge.instruction
        expr = instr.expression # This is an ast.Return
        log.printer.log_debug(5, f"[PredAbsPrecision DEBUG] ssa_from_return: edge='{edge.label()}', ssa_indices={ssa_indices}, expr={ast.dump(expr) if expr else 'None'}")
        
        if hasattr(instr, 'return_variable') and expr.value: # expr.value is the AST node being returned
            # The value being returned (e.g., variable 'r' in 'return r')
            returned_value_smt = _expr2smt(expr.value, ssa_indices) # uses current SSA of 'r'
            if hasattr(instr, 'target_variable') and instr.target_variable:
                 ret_storage_name = instr.target_variable
            else: # Fallback, less ideal
                 ret_storage_name = f"__retval_{edge.predecessor.get_function_name()}"

            lhs_return_storage = _ssa(ret_storage_name, _next(ret_storage_name, ssa_indices))
            log.printer.log_debug(5, f"[PredAbsPrecision DEBUG] ssa_from_return: {lhs_return_storage} = {returned_value_smt}")
            return Equals(lhs_return_storage, returned_value_smt)

        log.printer.log_debug(5, "[PredAbsPrecision DEBUG] ssa_from_return: No value returned or no target variable, returning TRUE.")
        return TRUE() # Return with no value

    @staticmethod
    def ssa_from_assign(edge: CFAEdge, ssa_indices: Dict[str, int]) -> FNode:
        instr = edge.instruction
        expr = instr.expression # This is an ast.Assign
        log.printer.log_debug(5, f"[PredAbsPrecision DEBUG] ssa_from_assign: edge='{edge.label()}', ssa_indices={ssa_indices}, expr={ast.dump(expr)}")

        if not isinstance(expr, ast.Assign) or not expr.targets:
            log.printer.log_debug(5, "[PredAbsPrecision WARN] ssa_from_assign: Expression is not a valid assignment, returning TRUE.")
            return TRUE()

        target_ast = expr.targets[0]
        
        if not isinstance(target_ast, ast.Name): # Simple assignment: x = ...
            log.printer.log_debug(5, f"[PredAbsPrecision WARN] ssa_from_assign: Assignment target '{ast.dump(target_ast)}' is not a simple Name, returning TRUE.")
            # TODO: Handle other target types like ast.Subscript (arrays/lists) or ast.Attribute if needed.
            return TRUE()

        var_name = target_ast.id
        
        # Value being assigned
        rhs_smt = _expr2smt(expr.value, ssa_indices) # uses current SSA for vars in RHS
        
        # Variable being assigned to (LHS)
        lhs_smt = _ssa(var_name, _next(var_name, ssa_indices)) # uses next SSA for LHS
        
        log.printer.log_debug(5, f"[PredAbsPrecision DEBUG] ssa_from_assign: {lhs_smt} = {rhs_smt}")
        return Equals(lhs_smt, _cast(rhs_smt, lhs_smt.get_type()))


    @staticmethod
    def ssa_from_assume(edge: CFAEdge, ssa_indices: Dict[str, int]) -> FNode:
        instr = edge.instruction
        expr = instr.expression # This is the assumption's AST expression
        log.printer.log_debug(5, f"[PredAbsPrecision DEBUG] ssa_from_assume: edge='{edge.label()}', ssa_indices={ssa_indices}, expr={ast.dump(expr)}")
        
        condition_smt = _expr2smt(expr, ssa_indices) # uses current SSA for variables
        log.printer.log_debug(5, f"[PredAbsPrecision DEBUG] ssa_from_assume: condition_smt={condition_smt}")
        return _bool(condition_smt)


    @staticmethod
    def from_cfa_edge(edge: CFAEdge, ssa_indices: Dict[str,int]) -> Optional[FNode]:
        """Computes the SMT formula for a given CFAEdge, advancing SSA indices."""
        log.printer.log_debug(5, f"[PredAbsPrecision DEBUG] from_cfa_edge: Processing edge {edge.label()} from {edge.predecessor.node_id} to {edge.successor.node_id}")
        kind = edge.instruction.kind

        if kind == InstructionType.STATEMENT:
            # In pycpa, Assign nodes are statements. Raise nodes are also statements.
            if isinstance(edge.instruction.expression, ast.Assign):
                return PredAbsPrecision.ssa_from_assign(edge, ssa_indices)
            elif isinstance(edge.instruction.expression, ast.Raise): # Handle raise by returning False
                log.printer.log_debug(5, f"[PredAbsPrecision DEBUG] from_cfa_edge: Encountered Raise statement, returning FALSE.")
                return FALSE() 
            else: # Other statements (like Expr for standalone calls) might be TRUE
                log.printer.log_debug(5, f"[PredAbsPrecision DEBUG] from_cfa_edge: Unhandled statement type {type(edge.instruction.expression)}, returning TRUE.")
                return TRUE()

        elif kind == InstructionType.ASSUMPTION:
            return PredAbsPrecision.ssa_from_assume(edge, ssa_indices)
        
        elif kind == InstructionType.CALL:
            # This handles parameter passing. Return value assignment is separate.
            return PredAbsPrecision.ssa_from_call(edge, ssa_indices)

        elif kind == InstructionType.RETURN:
            return PredAbsPrecision.ssa_from_return(edge, ssa_indices)
            
        elif kind == InstructionType.NONDET: # E.g. __VERIFIER_nondet_int()
            log.printer.log_debug(5, f"[PredAbsPrecision DEBUG] from_cfa_edge: Nondet instruction, using ssa_from_call logic.")
            return PredAbsPrecision.ssa_from_call(edge, ssa_indices) # Or a more specific nondet handler

        elif kind == InstructionType.REACH_ERROR: # Typically an ast.Call to reach_error()
            log.printer.log_debug(5, f"[PredAbsPrecision DEBUG] from_cfa_edge: Encountered REACH_ERROR, returning FALSE.")
            return FALSE() # Path becomes infeasible if reach_error is hit

        elif kind == InstructionType.EXIT or kind == InstructionType.ABORT:
             log.printer.log_debug(5, f"[PredAbsPrecision DEBUG] from_cfa_edge: Encountered {kind}, returning FALSE (path ends).")
             return FALSE() # Path terminates

        elif kind == InstructionType.NOP:
            log.printer.log_debug(5, f"[PredAbsPrecision DEBUG] from_cfa_edge: NOP instruction, returning TRUE.")
            return TRUE()
            
        else:
            log.printer.log_debug(5, f"[PredAbsPrecision WARN] from_cfa_edge: Unknown instruction kind {kind} for edge {edge.label()}, returning None.")
            return None # Or TRUE() if preferred for unknown ops

    @staticmethod
    def from_cfa(roots: List[CFANode], initial_globals: Optional[Set[FNode]] = None) -> PredAbsPrecision:
        """
        Creates an initial precision by extracting atomic predicates from all CFA edges.
        Predicates are stored globally for simplicity in this initial version.
        A more refined version would store them per-location or per-function.
        """
        log.printer.log_debug(5, f"[PredAbsPrecision INFO] Initializing precision from CFA with {len(roots)} root(s).")

        global_preds: Set[FNode] = initial_globals if initial_globals is not None else {TRUE(), FALSE()}

        processed_edges = set()
        
        worklist = []
        for root_node in roots:
            if root_node not in worklist:
                 worklist.append(root_node)
        
        seen_nodes = set(roots)

        while worklist:
            current_node = worklist.pop(0)
            log.printer.log_debug(5, f"[PredAbsPrecision DEBUG] from_cfa: Visiting node {current_node.node_id}")

            for edge in current_node.leaving_edges:
                if edge in processed_edges:
                    continue
                processed_edges.add(edge)

                # Use a temporary empty SSA map for predicate extraction, as we only want the structure.
                # Predicates in the precision are typically stored unindexed.
                formula_for_edge = PredAbsPrecision.from_cfa_edge(edge, {}) 
                if formula_for_edge is not None and formula_for_edge.get_type() == BOOL:
                    atoms = formula_for_edge.get_atoms()
                    # log.printer.log_debug(5, f"[PredAbsPrecision DEBUG] from_cfa: Edge {edge.label()}, formula {formula_for_edge}, atoms {atoms}")
                    for atom in atoms:
                        if not atom.is_true() and not atom.is_false(): # Avoid adding True/False as specific predicates
                            unindexed_atom = unindex_predicate(atom)
                            global_preds.add(unindexed_atom)
                            # For per-location:
                            # if edge.predecessor not in preds_map: preds_map[edge.predecessor] = set()
                            # preds_map[edge.predecessor].add(unindexed_atom)
                
                if edge.successor not in seen_nodes:
                    seen_nodes.add(edge.successor)
                    worklist.append(edge.successor)
        
        log.printer.log_debug(5, f"[PredAbsPrecision INFO] from_cfa: Extracted {len(global_preds)} unique global predicates.")
        # For per-location: return PredAbsPrecision(local_preds=preds_map, global_preds={TRUE(), FALSE()})
        return PredAbsPrecision(global_preds=global_preds)

