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
    BVLShl, BVAShr, BVOr, BVXor, BVAnd,
    substitute, get_env
)
from pysmt.typing import BV64, BOOL
from pysmt.fnode import FNode

from pycpa.analyses.ssa_helper import SSA

from pycpa.cfa import InstructionType, CFAEdge, CFANode # Assuming CFANode is hashable

from pycpa import log

import copy


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
            return SSA.ssa(v, ssa.get(v, 0))

        case ast.Constant(value=v):
            if isinstance(v, bool): return _bv(TRUE()) if v else _bv(FALSE())
            if isinstance(v, int):  return BV(v, 64)
            h = hashlib.md5(repr(v).encode()).hexdigest()[:8]
            log.printer.log_debug(1, f"[PredAbsPrecision WARN] _expr2smt: Unknown constant type {type(v)}, creating symbolic const_{h}")
            return SSA.ssa(f"const_{h}", 0) # Fallback for other const types

        case ast.BinOp(left=l, op=op_type, right=r): # Consolidate BinOp
            left_smt = _expr2smt(l, ssa)
            right_smt = _expr2smt(r, ssa)

            # Ensure consistent types for arithmetic ops, cast if necessary
            if not isinstance(op_type, (ast.Eq, ast.NotEq, ast.And, ast.Or)): # Non-boolean binary ops
                 # cast to BV64 if not already, common for arithmetic
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
                op_type : cmpop = ops[0]

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
            raise NotImplementedError()


        case _:
            log.printer.log_debug(5, f"[PredAbsPrecision ERROR] _expr2smt: Unsupported AST node type {type(node)}: {ast.dump(node)}. Returning TRUE as fallback.")
            return TRUE()


# --------------------------------------------------------------------------- #
#  Precision object (mapping from CFANode to predicate set)                   #
# --------------------------------------------------------------------------- #
class PredAbsPrecision:
    def __init__(self, preds: dict[CFANode,FNode]):
        self.predicates: dict[CFANode,FNode] = preds

    def __getitem__(self, location: CFANode) -> set[FNode]:
        """Allows dictionary-like access, e.g., precision[cfa_node]."""
        assert location in self.predicates
        return self.predicates.get(location, {TRUE()})

    def __contains__(self, location : CFANode) -> bool: 
        return location in self.predicates

    def __iter__(self): 
        return iter(self.predicates)
    def __len__(self): 
        return len(self.predicates)

    def __str__(self):
        return str({ str(n) : str(p) for n,p in self.predicates.items()})

    def __copy__(self):
        return PredAbsPrecision(
            copy.copy(self.predicates)
        )

    def __deepcopy__(self, mem):
        return PredAbsPrecision(
            copy.copy(self.predicates)
        )

    def __eq__(self, other):
        return self.predicates == other.predicates


    def get_predicates_for_location(self, location: CFANode) -> set[FNode]:
        """
        Retrieves all applicable predicates for a given CFA node
        """
        return self.predicates.get(location, {TRUE()})


    def add_global_predicates(self, new_preds: Iterable[FNode]):
        """Adds new global predicates"""
        for location in self.predicates:
            self.predicates[location].update(new_preds)

    def add_local_predicates(self, new_preds: dict[CFANode, Iterable[FNode]]):
        """Adds new predicates to location"""
        for location, preds in new_preds.items():
            if location not in self.predicates:
                self.predicates[location] = set()
            self.predicates[location].update(preds)

    @staticmethod
    def ssa_from_nondet(edge: CFAEdge, ssa_indices: dict[str, int]) -> FNode:
        instr = edge.instruction
        assert instr.kind == InstructionType.NONDET

        var_name = instr.target_variable
        assert isinstance(var_name, str)
        
        # here, we also advance the ssa index of the right side
        # as each nondet call gives an independent value
        rhs_smt = SSA.ssa('__nondet', SSA.next('__nondet', ssa_indices))
        
        # variable being assigned to (LHS), advance ssa index
        lhs_smt = SSA.ssa(var_name, SSA.next(var_name, ssa_indices)) 
        
        return Equals(lhs_smt, _cast(rhs_smt, lhs_smt.get_type()))

    @staticmethod
    def ssa_from_call(edge: CFAEdge, ssa_indices: Dict[str, int]) -> FNode:
        instr = edge.instruction
        log.printer.log_debug(5, f"[PredAbsPrecision DEBUG] ssa_from_call: edge='{edge.label()}', ssa_indices={ssa_indices}")

        # Handle regular function calls with parameter passing
        if not hasattr(instr, "param_names") or not hasattr(instr, "arg_names"):
            log.printer.log_debug(5, "[PredAbsPrecision DEBUG] ssa_from_call: No param_names or arg_names, returning TRUE.")
            return TRUE()

        conjuncts = []
        # 1. map each actual argument to the formal parameter
        #    formal_new_ssa = actual_current_ssa
        for formal, actual in zip(instr.param_names, instr.arg_names):
            rhs = _expr2smt(actual, ssa_indices)
            lhs = SSA.ssa(formal, SSA.next(formal, ssa_indices))
            conjuncts.append(Equals(lhs, rhs))
            log.printer.log_debug(5, f"[PredAbsPrecision DEBUG] ssa_from_call: Param assignment {lhs} = {rhs}")

        log.printer.log_debug(5, f"[PredAbsPrecision DEBUG] ssa_from_call: conjuncts={conjuncts}")
        return And(conjuncts) if conjuncts else TRUE()



    @staticmethod
    def ssa_from_return(edge: CFAEdge, ssa_indices: Dict[str, int]) -> FNode:
        return TRUE()

    @staticmethod
    def ssa_from_assign(edge: CFAEdge, ssa_indices: Dict[str, int]) -> FNode:
        instr = edge.instruction
        expr = instr.expression # This is an ast.Assign
        log.printer.log_debug(5, f"[PredAbsPrecision DEBUG] ssa_from_assign: edge='{edge.label()}', ssa_indices={ssa_indices}, expr={ast.dump(expr)}")

        if not isinstance(expr, ast.Assign) or not expr.targets:
            log.printer.log_debug(5, "[PredAbsPrecision WARN] ssa_from_assign: Expression is not a valid assignment, returning TRUE.")
            return TRUE()

        target_ast = expr.targets[0]
        assert isinstance(target_ast, ast.Name)

        var_name = target_ast.id
        
        # Value being assigned
        rhs_smt = _expr2smt(expr.value, ssa_indices) # uses current SSA for vars in RHS
        
        # Variable being assigned to (LHS)
        lhs_smt = SSA.ssa(var_name, SSA.next(var_name, ssa_indices)) # uses next SSA for LHS
        
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
            else:
                log.printer.log_debug(5, f"[PredAbsPrecision DEBUG] from_cfa_edge: statment {type(edge.instruction.expression)}, returning TRUE.")
                return TRUE()

        elif kind == InstructionType.ASSUMPTION:
            return PredAbsPrecision.ssa_from_assume(edge, ssa_indices)
        
        elif kind == InstructionType.CALL:
            # This handles parameter passing. Return value assignment is separate.
            return PredAbsPrecision.ssa_from_call(edge, ssa_indices)

        elif kind == InstructionType.RETURN:
            return PredAbsPrecision.ssa_from_return(edge, ssa_indices)
            
        elif kind == InstructionType.NONDET: # E.g. __VERIFIER_nondet_int()
            return PredAbsPrecision.ssa_from_nondet(edge, ssa_indices)

        else:
            log.printer.log_debug(5, f"[PredAbsPrecision DEBUG] from_cfa_edge: instruction does not require formula, returning TRUE.")
            return TRUE()

    @staticmethod
    def from_cfa(roots: List[CFANode], initial_globals: Optional[Set[FNode]] = None) -> PredAbsPrecision:
        """
        Creates an initial precision by extracting atomic predicates from all CFA edges.
        Predicates are stored globally for simplicity in this initial version.
        A more refined version would store them per-location.
        """
        log.printer.log_debug(5, f"[PredAbsPrecision INFO] Initializing precision from CFA with {len(roots)} root(s).")

        global_preds: set[FNode] = initial_globals if initial_globals is not None else {TRUE(), FALSE()}

        worklist = list(roots)
        seen_nodes = set(roots)

        predicates : dict[CFANode, set[FNode]] = dict()

        while worklist:
            current_node = worklist.pop(0)
            log.printer.log_debug(5, f"[PredAbsPrecision DEBUG] from_cfa: Visiting node {current_node.node_id}")

            if current_node not in predicates:
                predicates[current_node] = set()

            for edge in current_node.leaving_edges:
                formula_for_edge = PredAbsPrecision.from_cfa_edge(edge, {}) 
                if formula_for_edge is not None and formula_for_edge.get_type() == BOOL:
                    atoms = formula_for_edge.get_atoms()
                    for atom in atoms:
                        if not atom.is_true() and not atom.is_false(): # Avoid adding True/False as specific predicates
                            unindexed_atom = SSA.unindex_predicate(atom)
                            global_preds.add(unindexed_atom)
                
                if edge.successor not in seen_nodes:
                    seen_nodes.add(edge.successor)
                    worklist.append(edge.successor)
        
        for n in predicates:
            predicates[n] = global_preds

        return PredAbsPrecision(predicates)

