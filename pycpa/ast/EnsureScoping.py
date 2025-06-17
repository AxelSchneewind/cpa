import ast
import re

class EnsureScoping(ast.NodeTransformer):
    """
        AST transformer that makes variable identifiers unique by adding making them fully qualified
    """


    def __init__(self):
        self.scopes = list()
        self.tmp_counter = 0

    def _make_varname(self, name):
        return '_'.join(self.scopes) + '_' + name
    
    def _enter_scope(self, name=None):
        if name is not None:
            self.scopes.append(name)
        else:
            self.copes.append('anon_' + str(self.tmp_counter))
            self.tmp_counter += 1

    def _leave_scope(self):
        self.scopes.pop()
    
    def visit_FunctionDef(self, node) -> ast.FunctionDef:
        """
        """
        scope = node.name

        self._enter_scope(scope)

        for i, a in enumerate(node.args.args):
            node.args.args[i] = self.visit(a)
        for i, b in enumerate(node.body):
            node.body[i] = self.visit(b)

        self._leave_scope()

        return node

    def visit_ClassDef(self, node) -> ast.ClassDef:
        """
        """
        scope = node.name

        self._enter_scope(node.name)

        for i, b in enumerate(node.body):
            node.body[i] = self.visit(b)

        self._leave_scope()

        return node

    def visit_Call(self, node) -> ast.Call:
        '''Calls keep unqualified names
        '''
        for i, a in enumerate(node.args):
            node.args[i] = self.visit(a)
        return node

    def visit_Name(self, node) -> ast.Name:
        if node.id not in {'int', 'str', 'bool', 'float' }:
            node.id = self._make_varname(node.id)
        return node
            
    def visit_arg(self, node):
        return ast.arg(self._make_varname(node.arg))



              
