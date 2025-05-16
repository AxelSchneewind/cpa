from pysmt.shortcuts import *
import pysmt.typing as types
import pysmt

from pycpa.cfa import Instruction, InstructionType, CFANode

import ast
import astunparse

import re

from typing import Collection



# TODO: support more types 
class FormulaBuilder(ast.NodeVisitor):
    """ NodeVisitor that computes a formula from expressions on CFA-edges """

    # use bitvectors for all variables
    # creates a constant from the given value
    @staticmethod
    def BV(val):
        match val:
            case bool():
                result = get_env().formula_manager.BV(0, 64)
                if val:
                    return BVNot(result)
                return result
            case int():
                return get_env().formula_manager.BV(val, 64)
            case _:
                return get_env().formula_manager.BV(0, 64)

    # not used currently
    @staticmethod
    def Bool(val):
        match val:
            case bool():
                return get_env().formula_manager.Bool(val)
            case int():
                return get_env().formula_manager.Bool(val != 0)
            case _:
                return get_env().formula_manager.Bool(0)


    def __init__(self, instruction : InstructionType, current_type=dict(), enable_ssa=False, ssa_indices=dict()):
        """
            takes a single instruction and computes a formula from it
        """

        self.instruction = instruction
        self.current_type = current_type

        self.enable_ssa = enable_ssa
        self.ssa_indices = ssa_indices

        # types used in formulas
        self.int_type = types.BV64
        self.bool_type = types.BOOL

    
    def store_type(self, name, current):
        assert isinstance(name, str)
        self.current_type[name] = current

    def lookup_type(self, name):
        assert isinstance(name, str)
        return self.int_type

    def ssa_current_identifier(self, name):
        assert isinstance(name, str)
        pattern = r'[0-9]+$'
        assert re.match(name, pattern) is None

        if self.enable_ssa:
            if not name in self.ssa_indices:
                self.ssa_indices[name] = 0
            return name + str(self.ssa_indices[name])
        else:
            return name
    
    def ssa_advance_identifier(self, name):
        assert isinstance(name, str)
        pattern = r'[0-9]+$'
        assert re.match(name, pattern) is None

        if self.enable_ssa:
            if not name in self.ssa_indices:
                self.ssa_indices[name] = 0
            self.ssa_indices[name] += 1
            return name + str(self.ssa_indices[name])
        else:
            return name

    def visit(self, node, required_type=None, is_rvalue=True):
        """ generic visit function, overwritten to pass required_type and is_rvalue """

        t = str(type(node).__name__)
        attrname = 'visit_' + t

        result = None
        if hasattr(self, attrname):
            result = getattr(self, attrname)(node, required_type=self.int_type, is_rvalue=is_rvalue)
        else:
            print('not supported: %s' % t)
            result = self.BV(0)

        assert(required_type == None or get_type(result) == required_type), (node, get_type(result), required_type)
        return result

    def visit_Name(self, node, required_type, is_rvalue=True):
        var_name = self.ssa_current_identifier(node.id)

        if not is_rvalue:
            assert required_type is not None
            var_name = self.ssa_advance_identifier(node.id)
            self.store_type(node.id, required_type)
        elif required_type is None:
            required_type = self.lookup_type(node.id)

        return Symbol(var_name, required_type)

    def visit_Constant(self, node, required_type, **params):
        match required_type, node.n:
            case self.int_type, int():
                return self.BV(node.n)
            # case self.bool_type, int():
            #     return self.Bool(bool(node.n != 0))
            case None, int():
                return self.BV(node.n)
            # case str():
                # return types[str](node.n)
            case self.int_type, _:
                return self.BV(0)
            # case self.bool_type, _:
            #     return self.Bool(False)
            case None, _:
                return self.BV(0)
            case _:
                return self.BV(node.n)

    def visit_Subscript(self, node, required_type, is_rvalue=False):
        var_name = '%s[%s]' % (node.value.id, node.slice.value)
        name = self.ssa_current_identifier(var_name)
        if not is_rvalue:
            name = self.ssa_advance_identifier(var_name)
        return Symbol(name, self.int_type)

    def visit_UnaryOp(self, node, **params):
        operand = self.visit(node.operand)
        if isinstance(node.op, ast.Not):
            match get_type(operand):
                case self.bool_type:
                    return Not(operand)
                case self.int_type:
                    return Equals(operand, self.BV(0))
        elif isinstance(node.op, ast.USub):
            return BVNeg(operand)
        elif isinstance(node.op, ast.UAdd):
            return operand
        elif isinstance(node.op, ast.Invert):
            return BVNot(operand)
        else:
            raise NotImplementedError("Operator %s is not implemented!" % node.op)

    def visit_BoolOp(self, node, required_type, **params):
        left_result = self.visit(node.values[0])
        right_result = self.visit(node.values[1], required_type=get_type(left_result))

        result = None
        match node.op:
            case ast.And():
                result = And(left_result, right_result)
            case ast.Or():
                result = Or(left_result, right_result)
            case _:
                raise NotImplementedError("Operator %s is not implemented!" % op)
        return result

    def visit_Compare(self, node, required_type, **params):
        left_result = self.visit(node.left)
        right_result = self.visit(node.comparators[0], required_type=get_type(left_result))
        ltype = get_type(left_result)

        op = node.ops[0]
        result = None
        match op:
            case ast.Eq():
                match ltype:
                    # case self.bool_type:
                    #     result = Iff(left_result, right_result)
                    case self.int_type:
                        result = Ite(Equals(left_result, right_result), self.BV(True), self.BV(False))
            case ast.Gt():
                result = BVSGT(left_result, right_result)
            case ast.GtE():
                result = BVSGE(left_result, right_result)
            case ast.LT():
                result = BVSLT(left_result, right_result)
            case ast.LtE():
                result = BVSLE(left_result, right_result)
            case ast.NotEq():
                result = Ite(NotEquals(left_result, right_result), self.BV(True), self.BV(False))
            case _:
                raise NotImplementedError("Operator %s is not implemented!" % op)
        return result

    def visit_Return(self, node, required_type, **params):
        if node.value:
            right_result = self.visit(node.value, required_type)
            return Equals(Symbol('__ret', required_type), right_result)
        return self.Bool(True)

    def visit_Call(self, node, required_type, **params):
        if hasattr(self.instruction, 'target'):
            left  = Symbol(self.ssa_advance_identifier(self.instruction.target), self.int_type)
            right = Symbol(self.ssa_current_identifier('__ret'), self.int_type)
            return Equals(left, right)
        return self.Bool(True)
               

    def visit_Assign(self, node, **params):
        assert len(node.targets) == 1
        assert isinstance(node.targets[0], ast.Name), node.targets[0]

        result = None
        match node.value:
            case ast.List():
                assert isinstance(node.targets[0], ast.Name)
                name = node.targets[0].id
            
                clauses = []
                for i, expr in enumerate(node.value.elts):
                    val = self.visit(expr)

                    if val is not None:
                        var_name = '%s[%s]' % (name, i)
                        self.ssa_advance_index(name)
                        self.store_type(name, get_type(val))
                        clauses.append(Equals(Symbol(var_name, get_type(val)), val))
                result = And(clauses)

            case ast.Name() | ast.Num() | ast.Constant() | ast.Subscript() | ast.BinOp() | ast.UnaryOp():
                right_result = self.visit(node.value)
                left_result = self.visit(node.targets[0], required_type=get_type(right_result), is_rvalue=False)

                # assert isinstance(node.targets[0], Name)
                # left_result = Symbol()
                # assert isinstance(left_result, Symbol)
                # left_result = left_result   # TODO increment SSA index

                assert left_result is not None and right_result is not None, (astunparse.unparse(node))
                result = Equals(left_result, right_result)

            case ast.Compare():
                right_result = self.visit(node.value)
                left_result = self.visit(node.targets[0], required_type=get_type(right_result), is_rvalue=False)
                result = Equals(left_result, right_result)

            case ast.Call():
                right_result = Symbol('__ret', self.int_type)
                left_result = self.visit(node.targets[0], is_rvalue=False)
                result = Equals(left_result, right_result)

            case _:
                print(type(node.value))
                raise NotImplementedError()
        return result

    def visit_AugAssign(self, node, **params):
        # modified right side
        expr = ast.BinOp(
            ast.Name(
                node.target.id, ast.Load(),
            ), 
            node.op, 
            node.value,
        )
        ast.copy_location(node, expr)

        right_result = self.visit(expr)
        left_result = self.visit(node.target, required_type=get_type(right_result), is_rvalue=False)

        return Equals(left_result, right_result)
    
    def visit_BinOp(self, node, **params):
        left_result = self.visit(node.left)
        right_result = self.visit(node.right, required_type=get_type(left_result))

        op = node.op
        result = None
        match op:
            case ast.Add(): result = BVAdd(left_result, right_result)
            case ast.Sub(): result = BVMinus(left_result, right_result)
            case ast.Mult(): result = BVMul(left_result, right_result)
            case ast.Div(): result = BVSDiv(left_result, right_result)  # TODO: make fraction
            case ast.FloorDiv(): result = BVSDiv(left_result, right_result)
            case ast.Mod(): result = BVURem(left_result, right_result)
            case ast.Pow(): result = BVPow(left_result, right_result)
            case ast.LShift(): result = BVAShl(left_result, right_result)
            case ast.RShift(): result = BVAShr(left_result, right_result)
            case ast.BitOr(): result = BVOr(left_result, right_result)
            case ast.BitXor(): result = BVXor(left_result, right_result)
            case ast.BitAnd(): result = BVAnd(left_result, right_result)
            case _:
                raise NotImplementedError("Operator %s is not implemented!" % op)

        return result


class PredAbsPrecision:
    def __init__(self, predicates : Collection[pysmt.fnode]):
        self.predicates = predicates

    @staticmethod
    def from_cfa_edge(cfa_edge) -> pysmt.formula:
        match cfa_edge.instruction.expression:
            case ast.Assign() | ast.Compare() | ast.Expr() | ast.UnaryOp():
                return FormulaBuilder(cfa_edge, enable_ssa=False).visit(cfa_edge.instruction.expression)
            case ast.FunctionDef() | ast.Return() | ast.Call():
                pass # safe to ignore
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

