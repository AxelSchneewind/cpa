#!/usr/bin/env python

from pycpa import CFA

from pycpa.CPA import CPA
from pycpa.CPA import TransferRelation
from pycpa.CPA import StopSepOperator

import ast
import copy

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

    def visit_NameConstant(self, node):
        self.rstack.append(Value(node.value))

    def visit_UnaryOp(self, node):
        self.visit(node.operand)
        result = self.rstack.pop()
        if isinstance(node.op, ast.Not):
            self.rstack.append(result.__not__())
        elif isinstance(node.op, ast.USub):
            self.rstack.append(result.neg())
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
        if isinstance(op,ast.Eq):
            self.rstack.append(left_result.__equal__(comp_results[0]))
        elif isinstance(op,ast.Gt):
            self.rstack.append(left_result.gt(comp_results[0]))
        elif isinstance(op,ast.GtE):
            self.rstack.append(left_result.gte(comp_results[0]))
        elif isinstance(op,ast.Lt):
            self.rstack.append(left_result.lt(comp_results[0]))
        elif isinstance(op,ast.LtE):
            self.rstack.append(left_result.lte(comp_results[0]))
        elif isinstance(op,ast.NotEq):
            self.rstack.append(left_result.neq(comp_results[0]))
        elif isinstance(op,ast.Is):
            self.rstack.append(left_result.__is__(comp_results[0]))
        elif isinstance(op,ast.IsNot):
            self.rstack.append(left_result.__isnot__(comp_results[0]))
        elif isinstance(op,ast.In):
            self.rstack.append(left_result.__in__(comp_results[0]))
        elif isinstance(op,ast.NotIn):
            self.rstack.append(left_result.__notin__(comp_results[0]))
        else:
            # TODO Task 8: implement other comparison operators like >,<,>=,<=
            raise NotImplementedError("Operator %s is not implemented!" % op)

    # DONE Task 8: implement other operations like subtraction or multiplication for hidden programs
    def visit_Add(self, node):
        self.visit(node.left)
        left_result = self.rstack.pop()
        self.visit(node.right)
        right_result = self.rstack.pop()
        self.rstack.append(left_result.__add__(right_result))

    def visit_Sub(self, node):
        self.visit(node.left)
        left_result = self.rstack.pop()
        self.visit(node.right)
        right_result = self.rstack.pop()
        self.rstack.append(left_result.__sub__(right_result))

    def visit_Mul(self, node):
        self.visit(node.left)
        left_result = self.rstack.pop()
        self.visit(node.right)
        right_result = self.rstack.pop()
        self.rstack.append(left_result.__mul__(right_result))

    def visit_Div(self, node):
        self.visit(node.left)
        left_result = self.rstack.pop()
        self.visit(node.right)
        right_result = self.rstack.pop()
        self.rstack.append(left_result.__div__(right_result))

    def visit_Mod(self, node):
        self.visit(node.left)
        left_result = self.rstack.pop()
        self.visit(node.right)
        right_result = self.rstack.pop()
        self.rstack.append(left_result.__mod__(right_result))


    def get_value_of(self, varname):
        return (
            Value(self.valuation[varname])
            if varname in self.valuation
            else Value.get_top()
        )

    def update(self, other_valuation):
        for lhs, rhs in zip(self.lstack, self.rstack):
            if rhs == Value.get_top():
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

    def __init__(self, actual=None, top=False):
        assert not isinstance(actual, Value)
        if top == True and Value.__top != None:
            """ Virtually private constructor for Top."""
            raise Exception("There may only be one top state!")
        else:
            self.actual = actual

    def __equal__(self, other):
        if self is Value.get_top():
            return self
        if other is Value.get_top():
            return other
        else:
            return Value(self.actual == other.actual)

    def neq(self, other):
        if self is Value.get_top():
            return self
        if other is Value.get_top():
            return other
        else:
            return Value(self.actual != other.actual)

    # We need this for negation of Top, since both are True!
    def __not__(self):  
        if self == Value.get_top():
            return self
        else:
            return Value(not self.actual.__bool__())

    # DONE Task 8: greater than
    def gt(self,other):
        if self == Value.get_top() or other == Value.get_top():
            return Value.get_top()
        else:
            return Value(self.actual > other.actual)
    def lt(self,other):
        if self == Value.get_top() or other == Value.get_top():
            return Value.get_top()
        else:
            return Value(self.actual < other.actual)

    def gte(self,other):
        if self == Value.get_top() or other == Value.get_top():
            return Value.get_top()
        else:
            return Value(self.actual >= other.actual)
    def lte(self,other):
        if self == Value.get_top() or other == Value.get_top():
            return Value.get_top()
        else:
            return Value(self.actual <= other.actual)

    def __is__(self,other):
        if self == Value.get_top() or other == Value.get_top():
            return Value.get_top()
        else:
            return Value(self.actual is other.actual)
    def __isnot__(self,other):
        if self == Value.get_top() or other == Value.get_top():
            return Value.get_top()
        else:
            return Value(not self.actual is other.actual)

    def __in__(self,other):
        if self == Value.get_top() or other == Value.get_top():
            return Value.get_top()
        else:
            return Value(self.actual in other.actual)
    def __notin__(self,other):
        if self == Value.get_top() or other == Value.get_top():
            return Value.get_top()
        else:
            return Value(not self.actual in other.actual)


    # DONE Task 8: negation
    def neg(self):
        if self == Value.get_top():
            return self
        else:
            return Value(-self.actual)

    # DONE Task 8: return a Value that wraps the result of the addition.
    # remember to consider the case where at least one of the operands is top!
    def __add__(self, other):
        if self == Value.get_top() or other == Value.get_top():
            return Value.get_top()
        else:
            return Value(self.actual + other.actual)

    # DONE Task 8: implement other operations like subtraction or multiplication for hidden programs
    def __sub__(self, other):
        if self == Value.get_top() or other == Value.get_top():
            return Value.get_top()
        else:
            return Value(self.actual - other.actual)

    def __mul__(self, other):
        # multiplication with zero is special case:
        if self.actual == 0 or other.actual == 0:
            return Value(0)
        elif self == Value.get_top() or other == Value.get_top():
            return Value.get_top()
        else:
            return Value(self.actual * other.actual)

    def __div__(self, other):
        if self == Value.get_top() or other == Value.get_top():
            return Value.get_top()
        else:
            return Value(self.actual / other.actual)

    def __mod__(self, other):
        if self == Value.get_top() or other == Value.get_top():
            return Value.get_top()
        else:
            return Value(self.actual % other.actual)


# In[25]:


class ValueTransferRelation(TransferRelation):
    def get_abstract_successors(self, predecessor):
        raise NotImplementedError(
            "successors without edge not possible for Value Analysis!"
        )

    def get_abstract_successors_for_edge(self, predecessor, edge):
        v = ValueExpressionVisitor(predecessor.valuation)
        kind = edge.instruction.kind
        if kind == CFA.InstructionType.STATEMENT:
            v.visit(edge.instruction.expression)
            successor = ValueState(predecessor)
            v.update(successor.valuation)
            return [successor]
        elif kind == CFA.InstructionType.ASSUMPTION:
            v.visit(edge.instruction.expression)
            # lstack should be empty because there is no lhs in an assumption:
            assert len(v.lstack) == 0
            # there should be one value on rstack, namely what the assumption evaluated to:
            assert len(v.rstack) == 1
            result = v.rstack.pop()
            if result == Value.get_top():
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
        return MergeSepOperator.MergeSepOperator()

    def get_transfer_relation(self):
        return ValueTransferRelation()


