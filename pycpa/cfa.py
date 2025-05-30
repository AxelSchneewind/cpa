#!/usr/bin/env python

import ast
from graphviz import Digraph
from typing import List, Optional # Added Optional

from enum import Enum


from pycpa import log


class InstructionType(Enum):
    STATEMENT = 1,
    ASSUMPTION = 2,
    CALL = 3,
    RETURN = 4,
    RESUME = 5,
    NONDET = 6,
    EXIT = 7,
    ABORT = 8,
    REACH_ERROR = 9,
    EXTERNAL = 10,
    NOP = 11

builtin_identifiers = {
    'exit'                          : InstructionType.EXIT,
    'abort'                         : InstructionType.ABORT,
    'call'                          : InstructionType.CALL,
    'return'                        : InstructionType.RETURN, 
    'nondet'                        : InstructionType.NONDET,
    '__VERIFIER_nondet_char'        : InstructionType.NONDET,
    '__VERIFIER_nondet_short'       : InstructionType.NONDET,
    '__VERIFIER_nondet_int'         : InstructionType.NONDET,
    '__VERIFIER_nondet_long'        : InstructionType.NONDET,
    '__VERIFIER_nondet_uchar'       : InstructionType.NONDET,
    '__VERIFIER_nondet_ushort'      : InstructionType.NONDET,
    '__VERIFIER_nondet_uint'        : InstructionType.NONDET,
    '__VERIFIER_nondet_ulong'       : InstructionType.NONDET,
    'reach_error'                   : InstructionType.REACH_ERROR,
}

class Instruction:
    """
    An instruction can have different types, the most important ones being 
     - statements
     - assumptions
     - calls (to defined functions or builtins)
     - reacherror
    """

    def __init__(self, expression, kind=InstructionType.STATEMENT, **params):
        self.kind = kind
        self.expression = expression
        # Ensure 'parameters' attribute exists, even if empty
        if not hasattr(self, 'parameters'):
            self.parameters = {}

        for p_name, p_value in params.items(): # Corrected variable name here
            if not hasattr(self, p_name):
                setattr(self, p_name, p_value)
    
    def __str__(self):
        identifier = str(self.kind).replace('InstructionType.', '')
        # Ensure 'parameters' attribute exists before accessing it
        exit_code_val = '0' # Default value
        if hasattr(self, 'parameters') and 'exit_code' in self.parameters:
             exit_code_val = self.parameters['exit_code']
        elif hasattr(self, 'exit_code'): # Check if it's a direct attribute
             exit_code_val = self.exit_code


        if self.kind == InstructionType.EXIT:
            return '%s(%s)' % (identifier, exit_code_val)
        elif self.kind == InstructionType.CALL:
            # Ensure 'location' attribute exists for CALL instructions
            call_location = getattr(self, 'location', 'UNKNOWN_LOCATION')
            return 'jump %s' % (call_location)
        # Ensure 'identifier' attribute exists for other types if it's used
        # For now, let's use a generic representation if 'identifier' is missing
        elif hasattr(self, 'identifier'):
             return '%s' % self.identifier
        else:
             # Fallback string representation if 'identifier' is not present
             return f'{identifier}: {ast.unparse(self.expression) if hasattr(self.expression, "lineno") else str(self.expression)}'


    @staticmethod
    def assumption(expression, negated=False):
        if negated:
            expression = ast.UnaryOp(op=ast.Not(), operand=expression,
                lineno=expression.lineno, col_offset=expression.col_offset
            )
        return Instruction(expression, kind=InstructionType.ASSUMPTION, negated=negated)

    @staticmethod
    def statement(expression):
        return Instruction(expression)

    @staticmethod
    def builtin(expression : ast.Call, target_variable : str = '__ret', **params):
        assert isinstance(expression, ast.Call)
        # Ensure expression.func is an ast.Name node before accessing .id
        name = ""
        if isinstance(expression.func, ast.Name):
            name = str(expression.func.id)
        else:
            # Handle cases where func is not a simple name (e.g., attribute access)
            # For simplicity, we might raise an error or return a generic instruction
            log.printer.log_debug(1, f"[Instruction WARN] Builtin call to non-Name func: {ast.dump(expression.func)}. Treating as EXTERNAL.")
            return Instruction(expression, kind=InstructionType.EXTERNAL, target_variable=target_variable, **params)

        assert name in builtin_identifiers, f"Builtin '{name}' not recognized."
        return Instruction(expression, kind=builtin_identifiers[name], target_variable=target_variable, **params)

    @staticmethod
    def reacherror(expression, **params):
        return Instruction(expression, kind=InstructionType.REACH_ERROR, **params)

    @staticmethod
    def resume(expression : ast.Call, stackframe, call_edge, return_edge):
        assert isinstance(expression, ast.Call)
        return Instruction(expression, kind=InstructionType.RESUME, stackframe=stackframe, call_edge=call_edge, return_edge=return_edge)

    @staticmethod
    def ret(expression : ast.Return, return_variable : str = '__ret'): # Added default for return_variable
        assert isinstance(expression, ast.Return)
        return Instruction(expression, kind=InstructionType.RETURN, return_variable=return_variable)

    @staticmethod
    def call(expression : ast.Call, declaration : ast.FunctionDef, entry_point : 'CFANode', argnames : List[ast.arg], target_variable : str = '__ret', **params):
        assert isinstance(expression, ast.Call)
        assert isinstance(declaration, ast.FunctionDef)
        assert isinstance(entry_point, CFANode) # Forward declaration for CFANode
        
        # Handle cases where arg.arg might not be an ast.Name (e.g., if constants are passed as arg names somehow)
        param_names = []
        for p in declaration.args.args:
            if isinstance(p.arg, ast.Name):
                param_names.append(str(p.arg.id))
            elif isinstance(p.arg, str):
                 param_names.append(p.arg)
            else:
                raise ValueError(f"Unexpected type for parameter name: {type(p.arg)}")

        arg_names_str = []
        for p in argnames:
            if isinstance(p.arg, ast.Name):
                arg_names_str.append(str(p.arg.id))
            elif isinstance(p.arg, str):
                arg_names_str.append(p.arg)
            else:
                arg_names_str.append(str(p.arg)) # Simplified: convert to string

        return Instruction(
            expression, 
            kind=InstructionType.CALL, 
            location=entry_point, 
            declaration=declaration, 
            param_names=param_names, 
            arg_names=arg_names_str, 
            target_variable=target_variable, 
            **params
        )

    @staticmethod
    def nop(expression):
        return Instruction(expression, kind=InstructionType.NOP)


class CFANode:
    index = 0

    def __init__(self, function_name: Optional[str] = None): # MODIFIED
        self.node_id = CFANode.index
        self.entering_edges = list()
        self.leaving_edges = list()
        self.function_name = function_name # MODIFIED: Store function name
        CFANode.index += 1

    def get_function_name(self) -> Optional[str]: # NEW METHOD
        return self.function_name

    def __str__(self):
        func_info = f" (in {self.function_name})" if self.function_name else ""
        return f"({self.node_id}{func_info})"

    @staticmethod
    def merge(a: 'CFANode', b: 'CFANode') -> 'CFANode': # MODIFIED
        if a.function_name != b.function_name and b.function_name is not None:
            if a.function_name is not None:
                log.printer.log_debug(1, f"[CFANode WARN] Merging nodes from different functions: {a.function_name} and {b.function_name}. Keeping {a.function_name}.")
            # a.function_name remains as is. If b had one and a didn't, a would get it if we assigned.
            # Default: 'a's properties are primary.

        for entering_edge in b.entering_edges:
            entering_edge.successor = a
            a.entering_edges.append(entering_edge)
        for leaving_edge in b.leaving_edges:
            leaving_edge.predecessor = a
            a.leaving_edges.append(leaving_edge)
        
        # Clear b's edges as they are now transferred to a
        b.entering_edges = list()
        b.leaving_edges = list()

        return a

class CFAEdge:
    def __init__(self, predecessor, successor, instruction):
        self.predecessor: CFANode = predecessor # Type hint
        self.successor: CFANode = successor   # Type hint
        predecessor.leaving_edges.append(self)
        successor.entering_edges.append(self)
        self.instruction = instruction

    def __str__(self):
        return "%s -%s-> %s" % (
            str(self.predecessor),
            self.label(),
            str(self.successor),
        )

    def label(self):
        # Ensure expression exists and has lineno before trying to access it.
        lineno_info = ""
        if hasattr(self.instruction, 'expression') and hasattr(self.instruction.expression, 'lineno'):
            lineno_info = str(self.instruction.expression.lineno) + ': '
        
        label_text = ""
        if self.instruction.kind == InstructionType.ASSUMPTION:
            label_text = '[' + ast.unparse(self.instruction.expression).strip() + ']'
        elif self.instruction.kind == InstructionType.STATEMENT:
            label_text = ast.unparse(self.instruction.expression).strip()
        elif self.instruction.kind == InstructionType.CALL:
            # Ensure declaration and name exist
            func_name = "UNKNOWN_FUNC"
            if hasattr(self.instruction, 'declaration') and hasattr(self.instruction.declaration, 'name'):
                func_name = self.instruction.declaration.name.strip()
            label_text = func_name + '()'
        elif self.instruction.kind == InstructionType.RETURN:
            label_text = ast.unparse(self.instruction.expression).strip()
        else:
            return '< %s >' % self.instruction.kind
        
        return lineno_info + label_text


class CFACreator(ast.NodeVisitor):
    def __init__(self):
        self.current_function_name: Optional[str] = "_global_" # MODIFIED: Track current function
        self.global_root = CFANode(function_name=self.current_function_name) # MODIFIED
        self.entry_point = self.global_root
        self.roots = [self.global_root]
        self.node_stack = list()
        self.node_stack.append(self.global_root)
        self.continue_stack = list()
        self.break_stack = list()
        self.function_def = {} # Maps function name to ast.FunctionDef
        self.function_entry_point = {} # Maps function name to its entry CFANode

        self.inline = False # Not directly used in this simplified version for function_name

    def _new_cfa_node(self) -> CFANode: # Helper to create nodes with current function context
        return CFANode(function_name=self.current_function_name)

    def visit_FunctionDef(self, node : ast.FunctionDef):
        log.printer.log_debug(1, f"[CFACreator INFO] Visiting FunctionDef: {node.name}")
        outer_scope_function_name = self.current_function_name # Save outer scope
        self.current_function_name = node.name # Set current scope

        pre = self.node_stack.pop()

        post = self._new_cfa_node() # MODIFIED
        edge = CFAEdge(pre, post, Instruction.nop(node))
        self.node_stack.append(post)

        if node.name in builtin_identifiers:
            log.printer.log_debug(1, f'[CFACreator WARN] Builtin function {node.name} redefined, ignoring definition.')
            self.current_function_name = outer_scope_function_name # Restore outer scope
            return

        root = self._new_cfa_node() # MODIFIED
        self.function_def[node.name] = node
        self.function_entry_point[node.name] = root

        if node.name == 'main': # Or your designated entry function
            self.entry_point = root
            log.printer.log_debug(1, f"[CFACreator INFO] Set entry point to function: {node.name}")


        self.node_stack.append(root)
        self.roots.append(root) # Add function root to list of all roots

        ast.NodeVisitor.generic_visit(self, node) # Visits body, args etc.

        last_node_in_func_body = self.node_stack.pop() 


        self.current_function_name = outer_scope_function_name # MODIFIED: Restore outer scope
        log.printer.log_debug(1, f"[CFACreator INFO] Finished visiting FunctionDef: {node.name}")


    def visit_While(self, node : ast.While):
        entry_node = self.node_stack.pop()
        inside_loop_condition_check = self._new_cfa_node() # Node for condition re-evaluation / loop head

        CFAEdge(entry_node, inside_loop_condition_check, Instruction.assumption(node.test)) # True branch from condition
        
        body_entry_node = self._new_cfa_node() # Node after condition is true
        edge_true_cond = CFAEdge(inside_loop_condition_check, body_entry_node, Instruction.assumption(node.test))

        outside_loop_node = self._new_cfa_node() # Node after condition is false
        self.break_stack.append(outside_loop_node)
        edge_false_cond = CFAEdge(inside_loop_condition_check, outside_loop_node, Instruction.assumption(node.test, negated=True))

        self.continue_stack.append(inside_loop_condition_check) # Continue goes back to condition check

        self.node_stack.append(body_entry_node)
        for statement in node.body:
            self.visit(statement)
        
        body_exit_node = self.node_stack.pop()
        # Edge from end of loop body back to condition check
        CFAEdge(body_exit_node, inside_loop_condition_check, Instruction.nop(node)) # Represents going back to loop head

        self.node_stack.append(outside_loop_node) # Continue with flow after loop
        self.continue_stack.pop()
        self.break_stack.pop()

    def visit_Break(self, node : ast.Break):
        entry_node = self.node_stack.pop()
        # Break goes to the node designated by the innermost loop's break_stack
        if not self.break_stack:
            log.printer.log_debug(1, "[CFACreator ERROR] Break statement outside of loop.")
            # Create a dummy next node to allow parsing to continue, though this is an error
            next_node_after_break = self._new_cfa_node()
            self.node_stack.append(next_node_after_break)
            return
            
        CFAEdge(entry_node, self.break_stack[-1], Instruction.statement(node))
        # After a break, control flow is effectively "dead" from this point in the sequence
        # So, we create a new disconnected node for any subsequent statements in the *same block*
        # (which shouldn't exist if break is last, or should be unreachable).
        # The stack should point to this new "unreachable" part.
        unreachable_continuation_node = self._new_cfa_node()
        self.node_stack.append(unreachable_continuation_node)


    def visit_Continue(self, node : ast.Continue):
        entry_node = self.node_stack.pop()
        if not self.continue_stack:
            log.printer.log_debug(1, "[CFACreator ERROR] Continue statement outside of loop.")
            next_node_after_continue = self._new_cfa_node()
            self.node_stack.append(next_node_after_continue)
            return

        CFAEdge(entry_node, self.continue_stack[-1], Instruction.statement(node))
        # Similar to break, create a new disconnected node for subsequent statements in the same block
        unreachable_continuation_node = self._new_cfa_node()
        self.node_stack.append(unreachable_continuation_node)


    def visit_If(self, node : ast.If):
        entry_node = self.node_stack.pop()
        
        # Node for 'then' branch
        then_branch_node = self._new_cfa_node() # MODIFIED
        edge_true = CFAEdge(entry_node, then_branch_node, Instruction.assumption(node.test))
        
        # Node for 'else' branch
        else_branch_node = self._new_cfa_node() # MODIFIED
        edge_false = CFAEdge(entry_node, else_branch_node, Instruction.assumption(node.test, negated=True))
        
        # Visit 'then' body
        self.node_stack.append(then_branch_node)
        for statement in node.body:
            self.visit(statement)
        then_exit_node = self.node_stack.pop()
        
        # Visit 'else' body
        self.node_stack.append(else_branch_node)
        if node.orelse:
            for statement in node.orelse:
                self.visit(statement)
            else_exit_node = self.node_stack.pop()
        else: # No 'else' block, so flow continues from else_branch_node (which is after the false condition)
            else_exit_node = else_branch_node # Effectively, the 'false' assumption edge leads here directly

        # Merge exit points
        merged_exit_node = self._new_cfa_node() # MODIFIED
        CFAEdge(then_exit_node, merged_exit_node, Instruction.nop(node)) # NOP to join
        CFAEdge(else_exit_node, merged_exit_node, Instruction.nop(node)) # NOP to join
        
        self.node_stack.append(merged_exit_node)


    def visit_Expr(self, node : ast.Expr):
        # Handles expressions used as statements (e.g., a function call not part of an assignment)
        self.visit(node.value) # Visit the actual expression (e.g., the Call node)

    def visit_Assign(self, node : ast.Assign):
        entry_node = self.node_stack.pop()
        exit_node = self._new_cfa_node() # MODIFIED
        

        if isinstance(node.value, ast.Call):
            # This implies that the assignment target (node.targets[0]) is where the result of the call goes.
            # The _handle_Call method needs to know this target.
            assert isinstance(node.targets[0], ast.Name), "Assignment from call must target a simple Name for now."
            target_var_name = node.targets[0].id
            
            self.node_stack.append(entry_node)
            if self.inline:
                 self._handle_Call_inline(node.value, target_variable_name=target_var_name)
            else:
                 self._handle_Call(node.value, target_variable_name=target_var_name)
            # _handle_Call will have pushed its own exit_node onto the stack.
        else:
            # Regular assignment
            edge = CFAEdge(entry_node, exit_node, Instruction.statement(node))
            self.node_stack.append(exit_node)


    def visit_Return(self, node : ast.Return):
        entry_node = self.node_stack.pop()
        
        return_value_name = None
        if node.value: # If it's not 'return None'
            if isinstance(node.value, ast.Name):
                return_value_name = node.value.id
            else:
                # This case should ideally be handled by ExpandReturn preprocessor
                # which makes the return value always a simple Name (like __ret).
                log.printer.log_debug(1, f"[CFACreator WARN] Return statement value is not a simple Name: {ast.dump(node.value)}. This might not be handled correctly by SSA.")
                # As a fallback, try to unparse it, but this is not ideal for SSA.
                return_value_name = ast.unparse(node.value).strip()

        return_exit_node = self._new_cfa_node() # MODIFIED
        
        ret_instr = Instruction.ret(node, return_variable=return_value_name if return_value_name else "__ret_void") # Use a placeholder if no value
        
        edge = CFAEdge(entry_node, return_exit_node, ret_instr)
        self.node_stack.append(return_exit_node)


    def _handle_Call_inline(self, call_node : ast.Call, target_variable_name : Optional[str] = None):
        log.printer.log_debug(1, f"[CFACreator WARN] Inlining for call {ast.dump(call_node.func)} not fully implemented, treating as standard call.")
        self._handle_Call(call_node, target_variable_name)


    def _handle_Call(self, call_node : ast.Call, target_variable_name : Optional[str] = None):
        # target_variable_name is the 'x' in 'x = f()'
        entry_node = self.node_stack.pop() # Node before the call
        node_after_call = self._new_cfa_node() # Node where execution resumes after call returns

        assert isinstance(call_node.func, ast.Name), "Function calls must be by simple name."
        func_name_to_call = call_node.func.id

        # Argument names (as strings or ast.Name if they are variables)
        arg_name_nodes = [] # List of ast.arg
        for arg_val_ast in call_node.args:
            if isinstance(arg_val_ast, ast.Name):
                arg_name_nodes.append(ast.arg(arg=arg_val_ast.id)) # Store var name as string in ast.arg
            elif isinstance(arg_val_ast, ast.Constant):
                 arg_name_nodes.append(ast.arg(arg=str(arg_val_ast.value)))
            else:
                # Complex expressions as arguments should be preprocessed into temporary variables.
                # Assuming preprocessor handles this. If not, this is an error.
                raise NotImplementedError(f"Complex argument expressions like {ast.dump(arg_val_ast)} in call not supported without preprocessing.")

        if func_name_to_call in builtin_identifiers:
            # Builtin call (like nondet() or reach_error())
            # These are typically single edges. target_variable_name is where nondet stores its result.
            instr = Instruction.builtin(call_node, target_variable=target_variable_name if target_variable_name else "__ret_builtin")
            edge = CFAEdge(entry_node, node_after_call, instr)
        elif func_name_to_call in self.function_def:
            # Call to a user-defined function
            callee_func_def = self.function_def[func_name_to_call]
            callee_entry_cfa_node = self.function_entry_point[func_name_to_call]
            
            instr = Instruction.call(
                expression=call_node,
                declaration=callee_func_def,
                entry_point=callee_entry_cfa_node,
                argnames=arg_name_nodes, # list of ast.arg containing strings of actual arg names/values
                target_variable=target_variable_name if target_variable_name else "__ret_void" # Where 'x' in x=f() is stored
            )
            edge = CFAEdge(entry_node, node_after_call, instr) # Edge from pre-call to post-call node in caller
        else:
            log.printer.log_debug(1, f"[CFACreator WARN] Call to undefined function '{func_name_to_call}'. Treating as external/NOP.")
            # Create a NOP edge or an "external call" edge.
            instr = Instruction.nop(call_node) # Or a specific EXTERNAL instruction
            edge = CFAEdge(entry_node, node_after_call, instr)

        self.node_stack.append(node_after_call)


    def visit_Call(self, node : ast.Call):
        # This is called when a call appears as a standalone expression (e.g., "f();")
        # not as part of an assignment. So, no target_variable_name.
        if self.inline:
            return self._handle_Call_inline(node, target_variable_name=None)
        else:
            return self._handle_Call(node, target_variable_name=None)

    def visit_Assert(self, node : ast.Assert):
        log.printer.log_debug(1, f"[CFACreator INFO] Visiting Assert: {ast.unparse(node.test).strip()}")
        entry_node = self.node_stack.pop()
        node_after_assert_passes = self._new_cfa_node()
        
        # Edge if assertion holds
        CFAEdge(entry_node, node_after_assert_passes, Instruction.assumption(node.test))
        self.node_stack.append(node_after_assert_passes)


    def visit_Raise(self, node : ast.Raise):
        log.printer.log_debug(1, f"[CFACreator INFO] Visiting Raise statement. Treating as reach_error.")
        entry_node = self.node_stack.pop()
        error_node = self._new_cfa_node() # Node representing the error state
        edge = CFAEdge(entry_node, error_node, Instruction.reacherror(node))
        unreachable_continuation_node = self._new_cfa_node()
        self.node_stack.append(unreachable_continuation_node)



class Graphable: # Minimal interface for things that can be graphed
    def get_node_label(self): pass
    def get_edge_labels(self, other): pass
    def get_successors(self): pass
    def get_node_id(self): pass # Added for consistency with arg_to_dot

class GraphableCFANode(Graphable):
    def __init__(self, node):
        assert isinstance(node, CFANode)
        self.node = node

    def get_node_label(self):
        return str(self.node.node_id) + (f"\\n{self.node.function_name}" if self.node.function_name else "")


    def get_edge_labels(self, other_graphable_node: 'GraphableCFANode'): # Type hint
        return [
            edge.label()
            for edge in self.node.leaving_edges
            if edge.successor == other_graphable_node.node # Compare CFANodes
        ]

    def get_successors(self):
        return [GraphableCFANode(edge.successor) for edge in self.node.leaving_edges]
    
    def get_node_id(self): # Required by visual.py's to_dot functions
        return self.node.node_id

    def __eq__(self, other):
        if not isinstance(other, GraphableCFANode):
            return False
        return self.node == other.node # Compare underlying CFANodes

    def __hash__(self):
        return hash(self.node) # Hash underlying CFANode

