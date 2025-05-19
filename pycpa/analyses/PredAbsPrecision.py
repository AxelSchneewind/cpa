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
    And, Or, Not, Equals, LT, LE, GT, GE,
    Int, Symbol, Div, TRUE, FALSE
)
from pysmt.typing  import INT
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
    return Symbol(f"{var}#{idx}", INT)

def _next(var: str, ssa: Dict[str, int]) -> int:
    ssa[var] = ssa.get(var, 0) + 1
    return ssa[var]

# --------------------------------------------------------------------------- #
#  Expression → SMT (covers all needed cases)                                 #
# --------------------------------------------------------------------------- #
def _expr2smt(node: ast.AST, ssa: Dict[str, int]) -> FNode:
    def _bool(t: FNode) -> FNode:
        return t if t.get_type().is_bool_type() else Not(Equals(t, Int(0)))

    match node:
        # identifiers / literals ---------------------------------------------
        case ast.Name(id=v):
            return _ssa(v, ssa.get(v, 0))

        case ast.Constant(value=v):
            if isinstance(v, bool): return TRUE() if v else FALSE()
            if isinstance(v, int):  return Int(v)
            # other constant → fresh INT
            h = hashlib.md5(repr(v).encode()).hexdigest()[:8]
            return Symbol(f"const_{h}", INT)

        # arithmetic ----------------------------------------------------------
        case ast.BinOp(left=l, op=ast.Add(),  right=r):
            return _expr2smt(l, ssa) + _expr2smt(r, ssa)
        case ast.BinOp(left=l, op=ast.Sub(),  right=r):
            return _expr2smt(l, ssa) - _expr2smt(r, ssa)
        case ast.BinOp(left=l, op=ast.Mult(), right=r):
            return _expr2smt(l, ssa) * _expr2smt(r, ssa)
        case ast.BinOp(left=l, op=ast.Div(),  right=r):
            return Div(_expr2smt(l, ssa), _expr2smt(r, ssa))
        case ast.BinOp(left=l, op=ast.FloorDiv(), right=r):
            return Div(_expr2smt(l, ssa), _expr2smt(r, ssa))
        case ast.BinOp(left=l, op=ast.Mod(), right=r):
            a, b = _expr2smt(l, ssa), _expr2smt(r, ssa)
            return a - b * Div(a, b)

        # Boolean connectives -------------------------------------------------
        case ast.BoolOp(op=ast.And(), values=vs):
            return And([_bool(_expr2smt(v, ssa)) for v in vs])
        case ast.BoolOp(op=ast.Or(),  values=vs):
            return Or ([_bool(_expr2smt(v, ssa)) for v in vs])

        # unary ---------------------------------------------------------------
        case ast.UnaryOp(op=ast.Not(),  operand=o):
            return Not(_bool(_expr2smt(o, ssa)))
        case ast.UnaryOp(op=ast.USub(), operand=o):
            return -_expr2smt(o, ssa)

        # comparisons ---------------------------------------------------------
        case ast.Compare(left=l, ops=ops, comparators=comps):
            lhs, conjs = _expr2smt(l, ssa), []
            for op, rhs_ast in zip(ops, comps):
                rhs = _expr2smt(rhs_ast, ssa)
                conjs.append({
                    ast.Lt: LT, ast.LtE: LE,
                    ast.Gt: GT, ast.GtE: GE,
                    ast.Eq: Equals,
                    ast.NotEq: lambda a,b: Not(Equals(a,b))
                }[type(op)](lhs, rhs))
                lhs = rhs
            return And(conjs)
        
        # --------------------------------------------------------------
        # unknown function call -> fresh nondet INT
        # --------------------------------------------------------------
        case ast.Call(func=ast.Name(id=fname), args=args):
            h = hashlib.md5(("call_" + fname + str(len(args))).encode()).hexdigest()[:8]
            return Symbol(f"call_{fname}_{h}", INT)


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
    #  SSA builders used by PredAbsCPA                                   #
    # ------------------------------------------------------------------ #
    @staticmethod
    # def ssa_from_assign(edge: CFAEdge, ssa=None, ssa_indices=None) -> FNode:
    #     ssa = ssa if ssa is not None else (ssa_indices or {})
    #     assign: ast.Assign = edge.instruction.expression
    #     assert len(assign.targets) == 1 and isinstance(assign.targets[0], ast.Name)
    #     var = assign.targets[0].id
    #     lhs = _ssa(var, _next(var, ssa))
    #     rhs = _expr2smt(assign.value, ssa)
    #     return Equals(lhs, rhs)
    def ssa_from_assign(edge: CFAEdge, ssa=None, ssa_indices=None) -> FNode:
        ssa = ssa if ssa is not None else (ssa_indices or {})

        # ‼ Skip non-assignment statements (break, continue, pass, etc.)
        if not isinstance(edge.instruction.expression, ast.Assign):
            from pysmt.shortcuts import TRUE
            return TRUE()                 # no effect on the state

        assign: ast.Assign = edge.instruction.expression
        var  = assign.targets[0].id
        lhs  = _ssa(var, _next(var, ssa))
        rhs  = _expr2smt(assign.value, ssa)
        return Equals(lhs, rhs)

    @staticmethod
    def ssa_from_assume(edge: CFAEdge, ssa=None, ssa_indices=None) -> FNode:
        ssa = ssa or {}
        phi = _expr2smt(edge.instruction.expression, ssa)
        if getattr(edge.instruction, "negated", False):
            phi = Not(phi)
        return phi

    # ------------------------------------------------------------------ #
    #  Helpers for initial predicate mining                              #
    # ------------------------------------------------------------------ #
    @staticmethod
    def from_cfa_edge(edge: CFAEdge) -> FNode | None:
        k = edge.instruction.kind
        if k == InstructionType.STATEMENT:
            return PredAbsPrecision.ssa_from_assign(edge, {})
        if k == InstructionType.ASSUMPTION:
            return PredAbsPrecision.ssa_from_assume(edge, {})
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
