#!/usr/bin/env python

from pycpa.cfa import InstructionType

from pycpa.cpa import CPA
from pycpa.cpa import TransferRelation
from pycpa.cpa import StopSepOperator
from pycpa.cpa import MergeSepOperator

import ast
import copy

import astunparse
import astpretty

# ### Value Analysis via ValueAnalysisCPA
# 
# To achieve a minimal value analysis,
# we will design a CPA that realizes constant propagation and
# a PropertyCPA that enables us to specify reachability by checking whether the function `reach_error` was called.
# 
# To test our implementation, we use the following two example programs:


# #### Task 8: Supporting arithmetic operators in value analysis (10 points)
# 
# To support value analysis, the transfer relation of our CPA needs to understand the semantics of the arithmetic operators, such as `+,-,*,/,>,==`.
# Below is a skeleton of how a CPA for value analysis can be constructed.
# The implementation of arithmetic operators is left as TODOs.
# We again use the visitor pattern for the implementation.
# 
# (5 points for the implementation in class `ValueExpressionVisitor`; 5 points for each test program. Note that we will have hidden programs that may require more support of the arithmetic operators.)

# In[23]:


class ValueState:
    def __init__(self, other=None):
        if other:
            self.valuation = copy.copy(other.valuation)
        else:
            self.valuation = dict()

    def subsumes(self, other):
        return all(
            [
                not key in self.valuation or self.valuation[key] == value
                for (key, value) in other.valuation.items()
            ]
        )

    def __eq__(self, other):
        return self.valuation == other.valuation

    def __hash__(self):
        return tuple(
            (k, v)
            for (k, v) in sorted(self.valuation.items(), key=lambda item: item[0])
        ).__hash__()

    def __str__(self):
        return "{%s}" % ",".join(
            ["->".join((k, str(v))) for (k, v) in self.valuation.items()]
        )


# In[24]:


class ValueExpressionVisitor(ast.NodeVisitor):
    def __init__(self, valuation):
        self.valuation = valuation
        self.lstack = list()
        self.rstack = list()

    def visit_Name(self, node):
        if isinstance(node.ctx, ast.Store):
            self.lstack.append(node.id)
        elif isinstance(node.ctx, ast.Load):
            var_name = node.id
            self.rstack.append(self.get_value_of(var_name))

    def visit_Num(self, node):
        self.rstack.append(Value(node.n))

    def visit_Constant(self, node):
        self.rstack.append(Value(node.n))

    def visit_NameConstant(self, node):
        self.rstack.append(Value(node.value))

    def visit_UnaryOp(self, node):
        self.visit(node.operand)
        result = self.rstack.pop()
        if isinstance(node.op, ast.Not):
            self.rstack.append(result.do_not())
        elif isinstance(node.op, ast.USub):
            self.rstack.append(result.do_neg())
        elif isinstance(node.op, ast.UAdd):
            self.rstack.append(result) # unary add does not do anything for integers
        else:
            # TODO Task 8: implement other unary operators like unary negation
            raise NotImplementedError("Operator %s is not implemented!" % node.op)

    def visit_Compare(self, node):
        self.visit(node.left)
        left_result = self.rstack.pop()
        comp_results = list()
        for comparator in node.comparators:
            self.visit(comparator)
            comp_results.append(self.rstack.pop())
        # we only support simple compares like 1<2 for now, not something like 1<2<3:
        assert len(comp_results) == 1
        assert len(node.ops) == 1
        op = node.ops[0]
        result = None
        match op:
            case ast.Eq():
                result =left_result.do_eq(comp_results[0])
            case ast.Gt():
                result = left_result.do_gt(comp_results[0])
            case ast.GtE():
                result = left_result.do_ge(comp_results[0])
            case ast.Lt():
                result = left_result.do_lt(comp_results[0])
            case ast.LtE():
                result = left_result.do_le(comp_results[0])
            case ast.NotEq():
                result = left_result.do_neg(comp_results[0])
            case ast.Eq():
                result = left_result.do_eq(comp_results[0])
            case ast.Neq():
                result = left_result.do_ne(comp_results[0])
            case _:
                raise NotImplementedError("Operator %s is not implemented!" % op)
        self.rstack.append(result)

    # DONE Task 8: implement other operations like subtraction or multiplication for hidden programs
    def visit_Assign(self, node):
        self.visit(node.targets[0])
        self.visit(node.value)

    def visit_AugAssign(self, node):
        # modified right side
        expr = ast.BinOp(
            ast.Name(
                node.target.id, ast.Load(),
                lineno=node.lineno, col_offset=node.col_offset
            ), 
            node.op, 
            node.value,
            lineno=node.lineno, col_offset=node.col_offset
        )
        self.visit(expr)
        self.visit(node.target)
    
    def visit_BinOp(self, node):
        self.visit(node.left)
        left_result = self.rstack.pop()
        self.visit(node.right)
        right_result = self.rstack.pop()

        op = node.op
        result = None
        match op:
            case ast.Add():
                result = left_result.do_add(right_result)
            case ast.Sub():
                result = left_result.do_sub(right_result)
            case ast.Mult():
                result = left_result.do_mul(right_result)
            case ast.Div():
                result = left_result.do_truediv(right_result)
            case ast.FloorDiv():
                result = left_result.do_floordiv(right_result)
            case ast.Mod():
                result = left_result.do_mod(right_result)
            case ast.Pow():
                result = left_result.do_pow(right_result)
            case ast.LShift():
                result = left_result.do_lshift(right_result)
            case ast.RShift():
                result = left_result.do_rshift(right_result)
            case ast.BitOr():
                result = left_result.do_or(right_result)
            case ast.BitXor():
                result = left_result.do_xor(right_result)
            case ast.BitAnd():
                result = left_result.do_and(right_result)
            case ast.MatMult():
                result = left_result.do_matmul(right_result)
            case _:
                raise NotImplementedError("Operator %s is not implemented!" % op)

        self.rstack.append(result)


    def get_value_of(self, varname):
        return (
            Value(self.valuation[varname])
            if varname in self.valuation
            else Value.get_top()
        )

    def update(self, other_valuation):
        for lhs, rhs in zip(self.lstack, self.rstack):
            if rhs.is_top():
                other_valuation.pop(lhs, None)
            else:
                other_valuation[lhs] = rhs.actual

class Value:
    __top = None

    @staticmethod
    def get_top():
        """ Static access method. """
        if Value.__top is None:
            Value.__top = Value(top=True)
        return Value.__top

    def is_top(self):
        return self is Value.get_top()

    def __init__(self, actual=None, top=False):
        assert not isinstance(actual, Value)
        if top == True and Value.__top != None:
            """ Virtually private constructor for Top."""
            raise Exception("There may only be one top state!")
        else:
            self.actual = actual

    def do_eq(self, other):
        if self.is_top():
            return self
        if other.is_top():
            return other
        else:
            return Value(self.actual == other.actual)

    def do_ne(self, other):
        if self.is_top():
            return self
        if other.is_top():
            return other
        else:
            return Value(self.actual != other.actual)

    # We need this for negation of Top, since both are True!
    def do_not(self):  
        if self.is_top():
            return self
        else:
            return Value(not self.actual.__bool__())

    # DONE Task 8: greater than
    def do_gt(self,other):
        if self.is_top() or other.is_top():
            return Value.get_top()
        else:
            return Value(self.actual > other.actual)

    def do_lt(self,other):
        if self.is_top() or other.is_top():
            return Value.get_top()
        else:
            return Value(self.actual < other.actual)

    def do_ge(self,other):
        if self.is_top() or other.is_top():
            return Value.get_top()
        else:
            return Value(self.actual >= other.actual)
    def do_le(self,other):
        if self.is_top() or other.is_top():
            return Value.get_top()
        else:
            return Value(self.actual <= other.actual)

    # DONE Task 8: negation
    def do_neg(self):
        if self.is_top():
            return self
        else:
            return Value(-self.actual)

    def do_pos(self):
        if self.is_top():
            return self
        else:
            return Value(+self.actual)

    def do_invert(self):
        if self.is_top():
            return self
        else:
            return Value(~self.actual)


    def do_add(self, other):
        if self.is_top() or other.is_top():
            return Value.get_top()
        else:
            return Value(self.actual + other.actual)

    def do_sub(self, other):
        if self.is_top() or other.is_top():
            return Value.get_top()
        else:
            return Value(self.actual - other.actual)

    def do_mul(self, other):
        # multiplication with zero is special case:
        if self.actual == 0 or other.actual == 0:
            return Value(0)
        elif self.is_top() or other.is_top():
            return Value.get_top()
        else:
            return Value(self.actual * other.actual)

    def do_truediv(self, other):
        if self.is_top() or other.is_top():
            return Value.get_top()
        else:
            return Value(self.actual / other.actual)

    def do_floordiv(self, other):
        if self.is_top() or other.is_top():
            return Value.get_top()
        else:
            return Value(self.actual // other.actual)

    def do_mod(self, other):
        if self.is_top() or other.is_top():
            return Value.get_top()
        else:
            return Value(self.actual % other.actual)

    def do_pow(right_result):
        if right_result.actual == 0:
            return Value(1)
        if self.actual == 0 and right_result.actual != 0:
            return Value(0)
        if self.actual == 1 and right_result.actual != 0:
            return Value(1)
        if self.is_top() or other.is_top():
            return Value.get_top()
        else:
            return Value(self.actual ** right_result)

    def do_lshift(right_result):
        if self.is_top() or other.is_top():
            return Value.get_top()
        else:
            return Value(self.actual << other.actual)

    def do_rshift(right_result):
        if self.is_top() or other.is_top():
            return Value.get_top()
        else:
            return Value(self.actual >> other.actual)

    def do_or(right_result):
        if right_result.actual == ~(0):
            return Value(~0)
        if self.is_top() or other.is_top():
            return Value.get_top()
        else:
            return Value(self.actual | other.actual)

    def do_xor(right_result):
        if self.is_top() or other.is_top():
            return Value.get_top()
        else:
            return Value(self.actual ^ other.actual)

    def do_and(right_result):
        if right_result.actual == 0:
            return Value(0)
        if self.is_top() or other.is_top():
            return Value.get_top()
        else:
            return Value(self.actual & other.actual)

    def do_matmul(right_result):
        pass

# In[25]:


class ValueTransferRelation(TransferRelation):
    def get_abstract_successors(self, predecessor):
        raise NotImplementedError(
            "successors without edge not possible for Value Analysis!"
        )

    def get_abstract_successors_for_edge(self, predecessor, edge):
        v = ValueExpressionVisitor(predecessor.valuation)
        kind = edge.instruction.kind
        if kind == InstructionType.STATEMENT:
            v.visit(edge.instruction.expression)
            successor = ValueState(predecessor)
            v.update(successor.valuation)
            return [successor]
        elif kind == InstructionType.ASSUMPTION:
            v.visit(edge.instruction.expression)
            # lstack should be empty because there is no lhs in an assumption:
            assert len(v.lstack) == 0
            # there should be one value on rstack, namely what the assumption evaluated to:
            assert len(v.rstack) == 1
            result = v.rstack.pop()
            if result.is_top():
                return [predecessor]
            passed = True if result.actual else False
            return [predecessor] if passed else []
        else:
            raise ValueError("invalid value")


class ValueAnalysisCPA(CPA):
    def get_initial_state(self):
        return ValueState()

    def get_stop_operator(self):
        return StopSepOperator(ValueState.subsumes)

    def get_merge_operator(self):
        return MergeSepOperator()

    def get_transfer_relation(self):
        return ValueTransferRelation()


