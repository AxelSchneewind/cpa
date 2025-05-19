from pysmt.shortcuts import *
import pysmt.typing as types
import pysmt

from pycpa.cfa import Instruction, InstructionType, CFANode, CFAEdge
from pycpa.analyses.FormulaBuilder import FormulaBuilder

import ast
import astpretty

import re

from typing import Collection


class PredAbsPrecision:
    def __init__(self, predicates : Collection[pysmt.fnode]):
        self.predicates = predicates

    
    @staticmethod
    def ssa_from_assign(cfa_edge : CFAEdge, ssa_indices : dict[str,int] = dict()) -> pysmt.formula:
        """
            computes a formula in SSA-form from the given assignment
        """
        expression = cfa_edge.instruction.expression
        kind = cfa_edge.instruction.kind
        assert kind == InstructionType.STATEMENT
        assert isinstance(expression, ast.Assign)

        result = None
        match expression.value:
            case ast.Call():
                result = TRUE()
            case ast.Compare() | ast.BinOp() | ast.UnaryOp() | ast.BoolOp() | ast.Name() | ast.Constant():
                fb =  FormulaBuilder(cfa_edge.instruction, ssa_indices=ssa_indices)
                result = fb.visit(expression, required_type = FormulaBuilder.bool_type)
            case ast.Expr():
                result = TRUE()
            case ast.Assign():
                fb =  FormulaBuilder(cfa_edge.instruction, ssa_indices=ssa_indices)
                result = fb.visit(expression = FormulaBuilder.bool_type)
            case _:
                assert False, (f"need to add case for %s, %s" % (expression.value, ast.unparse(expression.value)))

        return result
    
    @staticmethod
    def ssa_from_assume(cfa_edge : CFAEdge, ssa_indices : dict[str,int] = dict()) -> pysmt.formula:
        """
            computes a formula in SSA-form from the given assume-expression
        """
        expression = cfa_edge.instruction.expression
        kind = cfa_edge.instruction.kind
        assert kind == InstructionType.ASSUMPTION, kind

        result = None
        match expression:
            case ast.Compare() | ast.BoolOp() | ast.UnaryOp() | ast.Name() | ast.Constant():
                fb =  FormulaBuilder(cfa_edge.instruction, ssa_indices=ssa_indices)
                result = fb.visit(expression, required_type=FormulaBuilder.bool_type)
            case ast.Call():
                result = TRUE()         # TODO
            case _:
                assert False, (f"need to add case for %s" % expression)
            
        return result

    @staticmethod
    def from_cfa_edge(cfa_edge : CFAEdge) -> pysmt.formula:
        match cfa_edge.instruction.expression:
            case ast.Assign() | ast.Compare() | ast.BoolOp() | ast.Expr() | ast.UnaryOp() | ast.BinOp():
                fb = FormulaBuilder(cfa_edge.instruction)
                return fb.visit(cfa_edge.instruction.expression, required_type=types.BV64)
            case ast.FunctionDef() | ast.Return() | ast.Call():
                return TRUE() # safe to ignore
            case _:
                print('from_cfa_edge: ignoring', cfa_edge.instruction.expression)


    @staticmethod
    def from_cfa(cfa_roots : Collection[CFANode]):
        result = set()
        result.add(TRUE())
        result.add(FALSE())

        waitlist = set()
        reached  = set()
        for c in cfa_roots:
            waitlist.add(c)

        while len(waitlist) > 0:
            node = waitlist.pop()
            reached.add(node)
            
            for edge in node.leaving_edges:
                formula = PredAbsPrecision.from_cfa_edge(edge)
                if formula is not None:
                    result.add(formula)
                if edge.successor not in reached:
                    waitlist.add(edge.successor)

        return result

    @staticmethod
    def empty_precision():
        return PredAbsPrecision({})

