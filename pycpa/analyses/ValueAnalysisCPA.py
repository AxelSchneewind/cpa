#!/usr/bin/env python

from pycpa.cfa import InstructionType

from pycpa.cpa import CPA, AbstractState, TransferRelation, StopSepOperator, MergeSepOperator

import ast
import copy

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


class ValueState(AbstractState):
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

    def _push_rvalue(self, rvalue):
        self.rstack.append(rvalue)

    def _push_lvalue(self, lvalue):
        assert isinstance(lvalue, str)
        self.lstack.append(lvalue)

    def _pop_rvalue(self):
        assert len(self.rstack) > 0
        return self.rstack.pop()

    def _pop_lvalue(self):
        assert len(self.lstack) > 0
        return self.lstack.pop()

    def visit_Name(self, node):
        if isinstance(node.ctx, ast.Store):
            self._push_lvalue(str(node.id))
        elif isinstance(node.ctx, ast.Load):
            var_name = node.id
            self._push_rvalue(self.get_value_of(var_name))

    def visit_Constant(self, node):
        self._push_rvalue(Value(node.n))

    def visit_Subscript(self, node):
        result = None
        if isinstance(node.ctx, ast.Load):
            self.visit(node.slice)
            sl  = self._pop_rvalue()

            self.visit(node.value)
            val = self._pop_rvalue()
            if val is None or sl is None or sl.is_top() or val.is_top():
                self._push_rvalue(Value.get_top())
            else:
                varname = '%s[%s]' % (str(val.actual), str(sl.actual))
                if varname in self.valuation:
                    self._push_rvalue(self.valuation[varname])
                else:
                    self._push_rvalue(Value.get_top())
        elif isinstance(node.ctx, ast.Store):
            assert isinstance(node.value, ast.Name), ('encountered invalid subscript: %s' % node)

            self.visit(node.slice)
            sl  = self._pop_rvalue()

            val = node.value.id

            if sl is None or sl.is_top():
                print('write to unknown memory location encountered, nuking value state')
                self.valuation = {}
            else:
                varname = '%s[%s]' % (str(val.actual if isinstance(val, Value) else val), str(sl.actual))
                self._push_lvalue(varname)

    def visit_UnaryOp(self, node):
        self.visit(node.operand)
        result = self._pop_rvalue()
        if isinstance(node.op, ast.Not):
            self._push_rvalue(result.do_not())
        elif isinstance(node.op, ast.USub):
            self._push_rvalue(result.do_neg())
        elif isinstance(node.op, ast.UAdd):
            self._push_rvalue(result.do_pos)
        elif isinstance(node.op, ast.Invert):
            self._push_rvalue(result.do_invert())
        else:
            raise NotImplementedError("Operator %s is not implemented!" % node.op)

    def visit_BoolOp(self, node):
        self.visit(node.values[0])
        left_result = self._pop_rvalue()
        self.visit(node.values[1])
        right_result = self._pop_rvalue()

        match node.op:
            case ast.And():
                result = left_result.do_and(right_result)
            case ast.Or():
                result = left_result.do_or(right_result)
            case _:
                raise NotImplementedError("Operator %s is not implemented!" % op)
        self._push_rvalue(result)


    def visit_Compare(self, node):
        self.visit(node.left)
        left_result = self._pop_rvalue()
        comp_results = list()
        for comparator in node.comparators:
            self.visit(comparator)
            comp_results.append(self._pop_rvalue())
        # we only support simple compares like 1<2 for now, not something like 1<2<3:
        assert len(comp_results) == 1, comp_results
        assert len(node.ops) == 1, node.ops
        op = node.ops[0]
        result = None
        match op:
            case ast.Eq():
                result = left_result.do_eq(comp_results[0])
            case ast.Gt():
                result = left_result.do_gt(comp_results[0])
            case ast.GtE():
                result = left_result.do_ge(comp_results[0])
            case ast.Lt():
                result = left_result.do_lt(comp_results[0])
            case ast.LtE():
                result = left_result.do_le(comp_results[0])
            case ast.NotEq():
                result = left_result.do_ne(comp_results[0])
            case ast.Eq():
                result = left_result.do_eq(comp_results[0])
            case _:
                raise NotImplementedError("Operator %s is not implemented!" % op)
        self._push_rvalue(result)

    def visit_Assign(self, node):
        assert len(node.targets) == 1

        if isinstance(node.value, ast.List) and isinstance(node.targets[0], ast.Name):
            name = node.targets[0].id
            
            for i, expr in enumerate(node.value.elts):
                self.visit(expr)
                val = self._pop_rvalue()
                if val is not None and not val.is_top():
                    self._push_lvalue('%s[%s]' % (name, i))
                    self._push_rvalue(val)
        else:
            self.visit(node.targets[0])
            self.visit(node.value)

    def visit_BinOp(self, node):
        self.visit(node.left)
        left_result = self._pop_rvalue()
        self.visit(node.right)
        right_result = self._pop_rvalue()

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

        self._push_rvalue(result)


    def get_value_of(self, varname):
        return (
            Value(self.valuation[varname])
            if varname in self.valuation
            else Value.get_top()
        )

    def update(self, other_valuation):
        for lhs, rhs in zip(self.lstack, self.rstack):
            if rhs.is_top():
                other_valuation.pop(str(lhs), None)
            else:
                other_valuation[str(lhs)] = rhs.actual

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
        if self.is_top() or other.is_top() or other.actual == 0:
            return Value.get_top()
        else:
            return Value(self.actual % other.actual)

    def do_pow(self, other):
        if other.actual == 0:
            return Value(1)
        if self.actual == 0 and other.actual != 0:
            return Value(0)
        if self.actual == 1 and other.actual != 0:
            return Value(1)
        if self.is_top() or other.is_top():
            return Value.get_top()
        else:
            return Value(self.actual ** other)

    def do_lshift(self, other):
        if self.is_top() or other.is_top() or other.actual < 0:
            return Value.get_top()
        else:
            return Value(self.actual << other.actual)

    def do_rshift(self, other):
        if self.is_top() or other.is_top() or other.actual < 0:
            return Value.get_top()
        else:
            return Value(self.actual >> other.actual)

    def do_or(self, other):
        if other.actual == ~(0):
            return Value(~0)
        if self.is_top() or other.is_top():
            return Value.get_top()
        else:
            return Value(self.actual | other.actual)

    def do_xor(self, other):
        if self.is_top() or other.is_top():
            return Value.get_top()
        else:
            return Value(self.actual ^ other.actual)

    def do_and(self, other):
        if other.actual == 0:
            return Value(0)
        if self.is_top() or other.is_top():
            return Value.get_top()
        else:
            return Value(self.actual & other.actual)

    def do_matmul(self, other):
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
            assert len(v.lstack) == 0, v.lstack
            # there should be one value on rstack, namely what the assumption evaluated to:
            assert len(v.rstack) == 1, v.rstack
            result = v._pop_rvalue()
            if result.is_top():
                return [copy.copy(predecessor)]
            passed = True if result.actual else False
            return [copy.copy(predecessor)] if passed else []
        elif edge.instruction.kind == InstructionType.CALL:
            newval = ValueState()
            newval.valuation = { edge.instruction.param_names[i] : predecessor.valuation[k] for i,k in enumerate(edge.instruction.arg_names) if k in predecessor.valuation }
            return [newval]
        elif edge.instruction.kind == InstructionType.NONDET:
            successor = ValueState(predecessor)
            if hasattr(edge.instruction, 'target'):
                successor.valuation[edge.instruction.target] = Value.get_top()
            else:
                successor.valuation['__ret'] = Value.get_top()
            return [successor]
        else:
            return [copy.copy(predecessor)]


class ValueAnalysisCPA(CPA):
    def get_initial_state(self):
        return ValueState()

    def get_stop_operator(self):
        return StopSepOperator(ValueState.subsumes)

    def get_merge_operator(self):
        return MergeSepOperator()

    def get_transfer_relation(self):
        return ValueTransferRelation()


