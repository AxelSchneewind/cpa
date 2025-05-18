from pysmt.shortcuts import *
import pysmt.typing as types
import pysmt

from pycpa.cfa import Instruction, InstructionType, CFANode

import ast
import astpretty
import astunparse

import re

from typing import Collection



# TODO: support more types 
class FormulaBuilder(ast.NodeVisitor):
    """ NodeVisitor that computes a formula from expressions on CFA-edges """

    # types used in formulas
    int_type = types.BV64
    bool_type = types.BOOL


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

    @staticmethod
    def BV_to_Bool(bv):
        return NotEquals(bv, FormulaBuilder.BV(0))

    @staticmethod
    def Bool_to_BV(b):
        assert get_type(b) == types.BOOL
        return Ite(b, FormulaBuilder.BV(1), FormulaBuilder.BV(0))


    def __init__(self, instruction : Instruction, current_type=dict(), ssa_indices=None, required_type=int_type):
        """
            takes a single instruction and computes a formula from it
        """

        self.instruction = instruction
        self.current_type = current_type

        self.enable_ssa = (ssa_indices is not None)
        self.ssa_indices = ssa_indices

        self.required_type = required_type

    
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

    def make_variable(self, name, required_type):
        if required_type is None:
            required_type = self.int_type
        return Symbol(name, required_type)

    def cast(self, value, required_type):
        actual_type = get_type(value)
        if required_type == actual_type:
            return value

        match required_type, actual_type:
            case self.int_type, self.bool_type:
                value = self.Bool_to_BV(value)
            case self.bool_type, self.int_type:
                value = self.BV_to_Bool(value)

        assert get_type(value) == required_type
        return value

    def make_equality(self, left, right):
        if get_type(right) != get_type(left):
            right = self.cast(right, get_type(left))
        match get_type(left):
            case self.bool_type:
                result = Iff(left, right)
            case self.int_type:
                result = Equals(left, right)
            case _:
                assert False
        return result

    def visit(self, node, required_type=None, is_rvalue=True):
        """ generic visit function, overwritten to pass required_type and is_rvalue """

        t = str(type(node).__name__)
        attrname = 'visit_' + t

        # 
        result = None
        if hasattr(self, attrname):
            result = getattr(self, attrname)(node, required_type=required_type, is_rvalue=is_rvalue)
        else:
            print('not supported: %s' % t)
            result = self.BV(0)

        # cast to desired type
        if required_type:
            result = self.cast(result, required_type)

        assert(required_type == None or get_type(result) == required_type)
        return result

    def visit_Name(self, node, required_type, is_rvalue=True):
        """ make new symbol """
        var_name = self.ssa_current_identifier(node.id)
        if not is_rvalue:
            var_name = self.ssa_advance_identifier(node.id)

        return self.make_variable(var_name, self.int_type)

    def visit_Constant(self, node, required_type, **params):
        match required_type, node.n:
            case self.int_type, int():
                result = self.BV(node.n)
            case self.bool_type, int():
                result = self.Bool(bool(node.n != 0))
            case None, int():
                result = self.BV(node.n)
            # case str():
                # result = types[str](node.n)
            case self.int_type, _:
                result = self.BV(0)
            case self.bool_type, _:
                result = self.Bool(False)
            case None, _:
                result = self.BV(0)
            case _:
                result = self.BV(node.n)
        return result

    def visit_Subscript(self, node, required_type, is_rvalue=False):
        var_name = '%s[%s]' % (node.value.id, node.slice.value)
        name = self.ssa_current_identifier(var_name)
        if not is_rvalue:
            name = self.ssa_advance_identifier(var_name)

        return self.make_variable(name, self.int_type)

    def visit_UnaryOp(self, node, **params):
        operand = self.visit(node.operand)
        if isinstance(node.op, ast.Not):
            match get_type(operand):
                case self.bool_type:
                    result = Not(operand)
                case self.int_type:
                    result = Equals(operand, self.BV(0))
        elif isinstance(node.op, ast.USub):
            result = BVNeg(operand)
        elif isinstance(node.op, ast.UAdd):
            result = operand
        elif isinstance(node.op, ast.Invert):
            result = BVNot(operand)
        else:
            raise NotImplementedError("Operator %s is not implemented!" % node.op)

        return result

    def visit_BoolOp(self, node, required_type, **params):
        left_result = self.visit(node.values[0], required_type=self.bool_type)
        right_result = self.visit(node.values[1], required_type=self.bool_type)

        result = None
        match node.op:
            case ast.And():
                result = And(left_result, right_result)
            case ast.Or():
                result = Or(left_result, right_result)
            case _:
                raise NotImplementedError("Operator %s is not implemented!" % op)

        assert get_type(result) == self.bool_type
        return result

    def visit_Compare(self, node, required_type, **params):
        left_result = self.visit(node.left)
        right_result = self.visit(node.comparators[0], required_type=get_type(left_result))
        ltype = get_type(left_result)
        assert get_type(left_result) == get_type(right_result)

        op = node.ops[0]
        result = None
        match op:
            case ast.Eq():
                result = self.make_equality(left_result, right_result)
            case ast.Gt():
                result = BVSGT(left_result, right_result)
            case ast.GtE():
                result = BVSGE(left_result, right_result)
            case ast.Lt():
                result = BVSLT(left_result, right_result)
            case ast.LtE():
                result = BVSLE(left_result, right_result)
            case ast.NotEq():
                result = Not(self.make_equality(left_result, right_result))
            case _:
                raise NotImplementedError("Operator %s is not implemented!" % op)

        assert get_type(result) == self.bool_type
        return result

    def visit_Return(self, node, required_type, **params):
        if required_type is None:
            required_type = self.int_type
        if node.value:
            right_result = self.visit(node.value, required_type)
            return self.make_equality(self.make_variable('__ret', required_type), right_result)
        return self.BV(1)

    def visit_Call(self, node, required_type, **params):
        if required_type is None:
            required_type = self.int_type
        if hasattr(self.instruction, 'target'):
            left  = self.make_variable(self.ssa_advance_identifier(self.instruction.target), self.int_type)
            right = self.make_variable(self.ssa_current_identifier('__ret'), self.int_type)
            return self.make_equality(left, right)
        return self.BV(1)
               

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
                        clauses.append(self.make_equality(self.make_variable(var_name, self.int_type), val))
                result = And(clauses), self.int_type

            case ast.Name() | ast.Num() | ast.Constant() | ast.Subscript() | ast.BinOp() | ast.UnaryOp() | ast.Compare() | ast.BoolOp():
                right_result = self.visit(node.value, required_type=self.int_type)
                left_result = self.visit(node.targets[0], required_type=self.int_type, is_rvalue=False)

                result = self.make_equality(left_result, right_result)
                assert get_type(left_result) == self.int_type

            case ast.Call():
                right_result = self.make_variable('__ret', required_type=self.int_type)
                left_result = self.visit(node.targets[0], required_type=self.int_type, is_rvalue=False)
                result = self.make_equality(left_result, right_result)
                assert get_type(left_result) == self.int_type

            case _:
                print(type(node.value))
                raise NotImplementedError()

        return result

    def visit_BinOp(self, node, **params):
        left_result = self.visit(node.left)
        right_result = self.visit(node.right, required_type=get_type(left_result))
        assert get_type(left_result) == get_type(right_result) == self.int_type

        op = node.op
        result = None
        match op:
            case ast.Add():      result = BVAdd(left_result, right_result)
            case ast.Sub():      result = BVMinus(left_result, right_result)
            case ast.Mult():     result = BVMul(left_result, right_result)
            case ast.Div():      result = BVSDiv(left_result, right_result)  # TODO: make Real
            case ast.FloorDiv(): result = BVSDiv(left_result, right_result)
            case ast.Mod():      result = BVURem(left_result, right_result)
            case ast.Pow():      result = BVPow(left_result, right_result)
            case ast.LShift():   result = BVAShl(left_result, right_result)
            case ast.RShift():   result = BVAShr(left_result, right_result)
            case ast.BitOr():    result = BVOr(left_result, right_result)
            case ast.BitXor():   result = BVXor(left_result, right_result)
            case ast.BitAnd():   result = BVAnd(left_result, right_result)
            case _:
                raise NotImplementedError("Operator %s is not implemented!" % op)

        return result



