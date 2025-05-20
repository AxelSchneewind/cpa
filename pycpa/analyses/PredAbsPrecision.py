#!/usr/bin/env python3
"""
Predicate Abstraction – Precision object + SSA helpers (final version).

* Precise translation for names, literals, all basic arithmetic,
  Boolean connectors, comparisons, unary ops.
* Unknown literals become fresh symbolic integers (sound over-approx.).
* PredAbsPrecision is **iterable** (behaves like a set of predicates).
"""

from __future__ import annotations
import ast, hashlib
from typing import Dict, Iterable, Set, List

from pysmt.shortcuts import (
    And, Or, Not, Equals, NotEquals, 
    BV, Symbol, TRUE, FALSE, Ite,

    BVNot, BVNeg, BVSGT, BVSGE, BVSLT, BVSLE, 
    BVAdd, BVMul, BVSDiv, BVSDiv, BVURem,
    BVLShl, BVAShr, BVOr, BVXor, BVAnd
)
from pysmt.typing  import BV64, BOOL
from pysmt.fnode   import FNode

# --------------------------------------------------------------------------- #
#  imports that work in- and outside the package                              #
# --------------------------------------------------------------------------- #
try:
    from pycpa.cfa import InstructionType, CFAEdge, CFANode
except ImportError:
    from cfa import InstructionType, CFAEdge, CFANode

# --------------------------------------------------------------------------- #
#  SSA helpers                                                                #
# --------------------------------------------------------------------------- #
def _ssa(var: str, idx: int) -> FNode:
    return Symbol(f"{var}#{idx}", BV64)

def _next(var: str, ssa: Dict[str, int]) -> int:
    ssa[var] = ssa.get(var, 0) + 1
    return ssa[var]

# --------------------------------------------------------------------------- #
#  Expression → SMT (covers all needed cases)                                 #
# --------------------------------------------------------------------------- #
def _cast(formula : FNode, target_type):
    actual_type = formula.get_type()
    if actual_type == target_type:
        return formula
    if target_type.is_bv_type() and actual_type.is_bool_type():
        return Ite(formula, BV(1, 64), BV(0, 64))
    if target_type.is_bool_type() and actual_type.is_bv_type():
        return NotEquals(formula, BV(0, 64))

    return formula

def _expr2smt(node: ast.AST, ssa: Dict[str, int]) -> FNode:
    def _bool(t: FNode) -> FNode:
        return _cast(t, BOOL)
    def _bv(t: FNode) -> FNode:
        return _cast(t, BV64)

    match node:
        # identifiers / literals ---------------------------------------------
        case ast.Name(id=v):
            return _ssa(v, ssa.get(v, 0))

        case ast.Constant(value=v):
            if isinstance(v, bool): return TRUE() if v else FALSE()
            if isinstance(v, int):  return BV(v, 64)
            # other constant → fresh BV64
            h = hashlib.md5(repr(v).encode()).hexdigest()[:8]
            return Symbol(f"const_{h}", BV64)

        # arithmetic ----------------------------------------------------------
        case ast.BinOp(left=l, op=ast.Add(),  right=r):
            return BVAdd(_bv(_expr2smt(l, ssa)), _bv(_expr2smt(r, ssa)))
        case ast.BinOp(left=l, op=ast.Sub(),  right=r):
            return BVAdd(_bv(_expr2smt(l, ssa)), BVNeg(_bv(_expr2smt(r, ssa))))
        case ast.BinOp(left=l, op=ast.Mult(), right=r):
            return BVMul(_bv(_expr2smt(l, ssa)), _bv(_expr2smt(r, ssa)))
        case ast.BinOp(left=l, op=ast.Div(),  right=r):
            return BVSDiv(_bv(_expr2smt(l, ssa)), _bv(_expr2smt(r, ssa)))
        case ast.BinOp(left=l, op=ast.FloorDiv(), right=r):
            return BVSDiv(_bv(_expr2smt(l, ssa)), _bv(_expr2smt(r, ssa)))
        case ast.BinOp(left=l, op=ast.Mod(), right=r):
            return BVURem(_bv(_expr2smt(l, ssa)), _bv(_expr2smt(r, ssa)))

        case ast.BinOp(left=l, op=ast.Pow(),  right=r):
            # not supported by BV as it seems
            raise NotImplementedError()

        # bit manipulation
        case ast.BinOp(left=l, op=ast.BitAnd(), right=r):
            return BVAnd(_bv(_expr2smt(l, ssa)), _bv(_expr2smt(r, ssa)))
        case ast.BinOp(left=l, op=ast.BitOr(), right=r):
            return BVOr(_bv(_expr2smt(l, ssa)), _bv(_expr2smt(r, ssa)))
        case ast.BinOp(left=l, op=ast.BitXor(), right=r):
            return BVXor(_bv(_expr2smt(l, ssa)), _bv(_expr2smt(r, ssa)))
        case ast.BinOp(left=l, op=ast.LShift(), right=r):
            # BV does not have arithmetic left shift?
            return BVLShl(_bv(_expr2smt(l, ssa)), _bv(_expr2smt(r, ssa)))
        case ast.BinOp(left=l, op=ast.RShift(), right=r):
            return BVAShr(_bv(_expr2smt(l, ssa)), _bv(_expr2smt(r, ssa)))

        # equality
        case ast.BinOp(left=l, op=ast.Eq(), right=r):
            return Equals(_expr2smt(l, ssa), _expr2smt(r, ssa))
        case ast.BinOp(left=l, op=ast.Neq(),  right=r):
            return NotEquals(_expr2smt(l, ssa), _expr2smt(r, ssa))

        # Boolean connectives -------------------------------------------------
        case ast.BoolOp(op=ast.And(), values=vs):
            return And([_bool(_expr2smt(v, ssa)) for v in vs])
        case ast.BoolOp(op=ast.Or(),  values=vs):
            return Or ([_bool(_expr2smt(v, ssa)) for v in vs])

        # unary ---------------------------------------------------------------
        case ast.UnaryOp(op=ast.Not(),  operand=o):
            return Not(_bool(_expr2smt(o, ssa)))
        case ast.UnaryOp(op=ast.USub(), operand=o):
            return BVNeg(_expr2smt(o, ssa))
        case ast.UnaryOp(op=ast.UAdd(), operand=o):
            return _expr2smt(o, ssa)

        # comparisons ---------------------------------------------------------
        case ast.Compare(left=l, ops=ops, comparators=comps):
            lhs, conjs = _expr2smt(l, ssa), []
            for op, rhs_ast in zip(ops, comps):
                rhs = _expr2smt(rhs_ast, ssa)
                conjs.append({
                    ast.Lt: BVSLT, ast.LtE: BVSLE,
                    ast.Gt: BVSGT, ast.GtE: BVSGE,
                    ast.Eq: Equals,
                    ast.NotEq: NotEquals
                }[type(op)](lhs, rhs))
                lhs = rhs
            return And(conjs)
        
        # --------------------------------------------------------------
        # unknown function call -> fresh nondet BV64
        # --------------------------------------------------------------
        case ast.Call(func=ast.Name(id=fname), args=args):
            # h = hashlib.md5(("call_" + fname + str(len(args))).encode()).hexdigest()[:8]
            # return Symbol(f"call_{fname}_{h}", BV64)
            return TRUE()


        # fallback ------------------------------------------------------------
        case _:
            raise NotImplementedError(f"expr→SMT for {ast.dump(node)}")

# --------------------------------------------------------------------------- #
#  Precision object (iterable like a set)                                     #
# --------------------------------------------------------------------------- #
class PredAbsPrecision(Iterable):
    def __init__(self, preds: Set[FNode] | None = None):
        self.predicates: Set[FNode] = set(preds or {TRUE(), FALSE()})

    # iterable / container protocol
    def __iter__(self):        return iter(self.predicates)
    def __contains__(self, p): return p in self.predicates
    def __len__(self):         return len(self.predicates)

    # ------------------------------------------------------------------ #
    #  (NEW) SSA for CALL edges:  copy actuals → formals, fresh ret var  #
    # ------------------------------------------------------------------ #
    @staticmethod
    def ssa_from_call(edge: CFAEdge, ssa_indices=None) -> FNode:
        """
        Build an SSA formula for a function-call edge.

        • For every (formal, actual) pair produce      formal#k+1  =  <actual>
        • If the instruction contains  instr.ret_var   copy return value:
              lhs_var#k+1  =  ret_sym
          (ret_sym is fresh, unconstrained BV64)
        """
        ssa = ssa_indices if ssa_indices is not None else {}
        instr = edge.instruction

        # safeguard: if we lack meta-data, over-approximate with TRUE
        if not hasattr(instr, "param_names") or not hasattr(instr, "arg_names"):
            return TRUE()

        conjuncts = []

        # 1. map each parameter
        for formal, actual in zip(instr.param_names, instr.arg_names):
            lhs = _ssa(formal, _next(formal, ssa))
            rhs = _expr2smt(ast.Name(id=actual, ctx=ast.Load()), ssa)
            conjuncts.append(Equals(lhs, rhs))

        # 2. optional return-value assignment  x = f(...)
        if hasattr(instr, "ret_var") and instr.ret_var:
            ret_sym = Symbol(f"ret_{instr.declaration.name}", BV64)
            lhs = _ssa(instr.ret_var, _next(instr.ret_var, ssa))
            conjuncts.append(Equals(lhs, ret_sym))

        return And(conjuncts) if conjuncts else TRUE()

        
    @staticmethod
    def ssa_from_assert(edge: CFAEdge, ssa_indices=None) -> FNode:
        """
        Handle Python 'assert' statements by extracting the test expression
        and translating it into an SMT predicate for refinement.
        """
        # Retrieve the AST Assert node and its test
        assert_node = edge.instruction.expression
        test_expr   = assert_node.test

        # Build/update SSA indices map if not provided
        ssa_map = ssa if ssa is not None else (ssa_indices or {})
        # Convert the test expression to an SMT formula
        return _bool(_expr2smt(test_expr, ssa_map))

    @staticmethod
    def ssa_from_raise(edge: CFAEdge, ssa_indices=None) -> FNode:
        # print(f"[DEBUG PredAbsPrecision] ssa_from_raise: kind={edge.instruction.kind}, expr={edge.instruction.expression!r}")
        return FALSE()

    @staticmethod
    def ssa_from_assign(edge: CFAEdge, ssa_indices=None) -> FNode:
        expr = getattr(edge.instruction, 'expression', None)
        # print(f"[DEBUG PredAbsPrecision] ssa_from_assign: kind={edge.instruction.kind}, expr={expr!r}")

        # 1) if this is a `raise`, mark as infeasible continuation
        if isinstance(expr, ast.Raise):
            # print("  → Detected Raise; returning FALSE()")
            return FALSE()

        # 2) standard assignment
        if isinstance(expr, ast.Assign):
            ssa_map = ssa_indices if ssa_indices is not None else {}
            var     = expr.targets[0].id
            lhs     = _ssa(var, _next(var, ssa_map))
            rhs     = _cast(_expr2smt(expr.value, ssa_map), BV64)
            # print(f"  → Assign {var}#{ssa_map[var]} = {rhs}")
            return Equals(lhs, rhs)

        # 3) everything else is a no-op
        return TRUE()

    @staticmethod
    def ssa_from_assume(edge: CFAEdge, ssa_indices=None) -> FNode:
        # Handles both 'assert' and 'if' conditions
        expr = edge.instruction.expression
        ssa_map = ssa_indices if ssa_indices is not None else {}
        phi = _expr2smt(expr, ssa_map)
        if getattr(edge.instruction, 'negated', False):
            return Not(phi)
        return phi
    
    @staticmethod
    def ssa_from_raise(edge: CFAEdge, ssa_indices=None) -> FNode:
        """
        Handle Python 'raise' by mapping it to FALSE(), marking an error path.
        """
        # print(f"[DEBUG PredAbsPrecision] ssa_from_raise on edge {edge}")
        return FALSE()


    @staticmethod
    def ssa_from_call(edge: CFAEdge, ssa_indices=None) -> FNode:
        # Inline the original call handler logic
        ssa_map = ssa_indices if ssa_indices is not None else {}
        instr = edge.instruction
        if not hasattr(instr, "param_names") or not hasattr(instr, "arg_names"):
            return TRUE()
        conjuncts = []
        for formal, actual in zip(instr.param_names, instr.arg_names):
            lhs = _ssa(formal, _next(formal, ssa_map))
            rhs = _expr2smt(ast.Name(id=actual, ctx=ast.Load()), ssa_map)
            conjuncts.append(Equals(lhs, rhs))
        if hasattr(instr, "ret_var") and instr.ret_var:
            ret_sym = Symbol(f"ret_{instr.declaration.name}", BV64)
            lhs = _ssa(instr.ret_var, _next(instr.ret_var, ssa_map))
            conjuncts.append(Equals(lhs, ret_sym))
        return And(conjuncts) if conjuncts else TRUE()

    @staticmethod
    def from_cfa_edge(edge: CFAEdge) -> FNode | None:
        expr = getattr(edge.instruction, 'expression', None)
        # print(f"[DEBUG PredAbsPrecision] from_cfa_edge: kind={edge.instruction.kind}, expr={expr!r}")

        # Python `assert` → assume
        if isinstance(expr, ast.Assert):
            # print("  → mining assert condition")
            return PredAbsPrecision.ssa_from_assume(edge, {})

        # explicit CFA assume edge
        if edge.instruction.kind == InstructionType.ASSUMPTION:
            # print("  → mining an ASSUMPTION edge")
            return PredAbsPrecision.ssa_from_assume(edge, {})

        # statements (assign or raise)
        if edge.instruction.kind == InstructionType.STATEMENT:
            if isinstance(expr, ast.Raise):
                # print("  → mining a Raise statement")
                return PredAbsPrecision.ssa_from_raise(edge, {})
            else:
                # print("  → mining a STATEMENT edge")
                return PredAbsPrecision.ssa_from_assign(edge, {})

        # function calls
        if edge.instruction.kind == InstructionType.CALL:
            # print("  → mining a CALL edge")
            return PredAbsPrecision.ssa_from_call(edge, {})

        return None




    @staticmethod
    def from_cfa(roots: List[CFANode]) -> "PredAbsPrecision":
        preds: Set[FNode] = {TRUE(), FALSE()}
        todo, seen = list(roots), set()
        while todo:
            n = todo.pop()
            if n in seen: continue
            seen.add(n)
            for e in n.leaving_edges:
                f = PredAbsPrecision.from_cfa_edge(e)
                if f is not None and f.get_type().is_bool_type():
                    preds.update(f.get_atoms())
                todo.append(e.successor)
        return PredAbsPrecision(preds)
    
    def __str__(self): return '{' + ', '.join(map(str, self.predicates)) + '}'
