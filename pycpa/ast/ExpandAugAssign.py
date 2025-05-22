import ast
import re
import copy

class ExpandAugAssign(ast.NodeTransformer):
    """
        AST transformer that transform augmented assignments into normal ones
    """

    def __init__(self):
        pass

    def visit_AugAssign(self, node) -> ast.AugAssign:
        assign = None
        match node.target:
            case ast.Name() | ast.Subscript():
                lvalue = copy.copy(node.target)
                lvalue.ctx = ast.Store()
                rvalue = copy.copy(node.target)
                rvalue.ctx = ast.Load()

                assign = ast.Assign(
                    targets =[ lvalue ], 
                    value = ast.BinOp( rvalue,  node.op, node.value )
                )
                ast.copy_location(assign, node)
                ast.fix_missing_locations(assign)
            case _:
                assert False, node.target

        assert isinstance(assign, ast.Assign)
        return assign