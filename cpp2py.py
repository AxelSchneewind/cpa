# taken from https://pypi.org/project/cpp2py/ with small fixes applied

#from .cparselite import read_funtion_def
from pycparser import c_parser
from pycparser import c_ast
import pycparser
import io

import re

tab = '\t'
def write_one_line(buf, depth):
    return f'{tab:.{depth}}{buf}\n'

class Ast2Py:
    def __init__(self):
        self.m_depth = 0
        self.import_file_list=[]

    def import_list(self):
        ret = ''
        self.import_file_list = list(set(self.import_file_list))
        for i in self.import_file_list:
            ret += f'from {i} import *\n'
        return ret

    def ast2py(self, ast,start_line=0):
        ret = ''
        for i in ast.ext:
            ret += self.ast2py_one_node(i)
        return ret

    def ast2py_fast(self, ast, filelike):
        self.stack = list()
        depth = 0

        # uppermost level of ast
        for i in reversed(ast.ext):
            self.push_expr(i)
            self.push_newline(depth)

        while len(self.stack) > 0:
            element = self.stack.pop()
            match element:
                case str():
                    filelike.write(element)
                case int():
                    filelike.write('\n' + '\t'*element)
                    depth = element
                case _:
                    self.ast2py_fast_one_node(element, depth)
        return

    def push_newline(self, depth):
        assert isinstance(depth, int)
        self.stack.append(depth)

    def push_expr(self, expr):
        assert not isinstance(expr, int)
        self.stack.append(expr)

    def ast2py_fast_one_node(self, n, depth):
        match n:
            case c_ast.FuncDef():
                self.push_newline(depth)
                self.push_expr(n.body)
                self.push_newline(depth + 1)
                self.push_expr('):')

                arg_list = []
                if n.decl.type.args:
                    for i in reversed(n.decl.type.args.params[1:]):
                        self.push_expr(i)
                        self.push_expr(',')
                    self.push_expr(n.decl.type.args.params[0])

                self.push_expr(f'def {n.decl.name} (')

            case c_ast.Typedef():
                self.push_expr(n.type.type)
                self.push_expr(' = ')
                self.push_expr(n.type.declname)

            # TODO: initlist

            case c_ast.Compound():
                if n.block_items and len(n.block_items) > 0:
                    for i in reversed(n.block_items[1:]):
                        self.push_expr(i)
                        self.push_newline(depth)
                    self.push_expr(n.block_items[0])
                else:
                    self.push_newline(depth)
                    self.push_expr('pass')

            case c_ast.EmptyStatement():
                self.push_newline(depth)
                self.push_expr('pass')

            case c_ast.Return():
                self.push_newline(depth)
                if n.expr:
                    self.push_expr(n.expr)
                self.push_expr('return ')

            case c_ast.Constant():
                py_constant = str(n.value)
                if re.match(r'^0+x', py_constant): # hex, done
                    pass
                elif re.match(r'^0', py_constant): # octal, done
                    py_constant = re.sub(r'^0+[^x]',  '0o', py_constant)

                py_constant = re.sub(r'[ULul]+$', '', py_constant)
                if len(py_constant) == 0 or py_constant == '0o':
                    py_constant = '0'
                self.push_expr(py_constant)

            case c_ast.ID():
                self.push_expr(n.name)


            case c_ast.Typename():
                selected = 'int'
                match n.name:
                    case 'char':
                        selected = 'byte'
                    case 'int' | 'short' | 'long':
                        selected = 'int'
                    case 'void':
                        selected = 'NoneType'
                    case 'float' | 'double':
                        selected  = 'float'
                    case _:
                        pass
                self.push_expr(selected)

            case c_ast.IdentifierType():
                selected = 'int'
                if n.names and len(n.names) > 0:
                    for t in n.names:
                        match t:
                            case 'char':
                                selected = 'byte'
                            case 'int' | 'short' | 'long':
                                selected = 'int'
                            case 'void':
                                selected = 'NoneType'
                            case 'float' | 'double':
                                selected  = 'float'
                            case _:
                                pass
                self.push_expr(selected)

            case c_ast.Struct():
                if n.decls:
                    name = n.name
                    for d in reversed(n.decls):
                        self.push_newline(depth + 2)
                        self.push_expr(d)
                        self.push_expr('self.')
                    self.push_newline(depth + 2)

                    self.push_expr('):')
                    for d in reversed(n.decls):
                        self.push_expr(' = None')
                        self.push_expr(d)
                        self.push_expr(', ')

                    self.push_expr('def __self__(self')
                    self.push_newline(depth + 1)
                    self.push_expr(': ')
                    self.push_expr(name)
                    self.push_expr('class ')
                    self.push_newline(depth)

            case c_ast.TypeDecl():
                self.push_expr(n.type)
                self.push_expr(':')
                self.push_expr(n.declname)

            case c_ast.Decl():
                if n.init is not None:
                    self.push_expr(n.init)
                    self.push_expr(' = ')
                    self.push_expr(n.type.type)
                    self.push_expr(' : ')
                    self.push_expr(n.name)
                else:
                    #add char* support
                    if isinstance(n.type, c_ast.PtrDecl) and isinstance(n.type.type, c_ast.TypeDecl) and isinstance(n.type.type.type, c_ast.IdentifierType):
                        if n.type.type.type.names ==['char']:
                            ostr =  f'{n.declname} = CharPtr()'
                            self.import_file_list.append('cpp2py.cpp2py_ctype')
                            self.push_expr(ostr)
                    elif isinstance(n.type, c_ast.ArrayDecl) \
                        and isinstance(n.type.type, c_ast.TypeDecl) and \
                        isinstance(n.type.type.type, c_ast.IdentifierType):
                            identifier = n.type.type.declname
                            typ = n.type.type.type
                            dim = n.type.dim
                            self.push_expr(') ]')
                            self.push_expr(dim)
                            self.push_expr('() for i in range(')
                            self.push_expr(typ)
                            self.push_expr(' = [ ')
                            self.push_expr(identifier)
                            self.import_file_list.append('cpp2py.cpp2py_ctype')
                    elif isinstance(n.type, c_ast.Struct):
                        if n.type.decls:
                            name = n.type.name
                            for d in reversed(n.type.decls):
                                self.push_expr(d.name)
                                self.push_expr(' = ')
                                self.push_expr(d.name)
                                self.push_expr('self.')
                                self.push_newline(depth + 2)
        
                            self.push_expr('):')
                            for d in reversed(n.type.decls):
                                self.push_expr(' = None')
                                self.push_expr(d.type.type)
                                self.push_expr(' : ')
                                self.push_expr(d.name)
                                self.push_expr(', ')
        
                            self.push_expr('def __self__(self')
                            self.push_newline(depth + 1)
                            self.push_expr(': ')
                            self.push_expr(name)
                            self.push_expr('class ')
                            self.push_newline(depth)

                    else:
                        pass
                        # self.push_expr(')')
                        # self.push_expr(n.type.type)
                        # self.push_expr(': (')
                        # self.push_expr(n.type.declname)
                        # self.push_newline(depth)

            case c_ast.Assignment():
                self.push_expr(n.rvalue)
                self.push_expr(' ')
                self.push_expr(n.op)
                self.push_expr(' ')
                self.push_expr(n.lvalue)


            case c_ast.StructRef():
                self.push_expr(n.field)
                self.push_expr('.')
                self.push_expr(n.name)

            case c_ast.ArrayRef():
                # TODO fix
                self.push_expr('[0]')
                self.push_expr(n.name)

            case c_ast.Break():
                self.push_newline(depth)
                self.push_expr('break')

            case c_ast.Continue():
                self.push_newline(depth)
                self.push_expr('continue')

            case c_ast.DoWhile():
                self.push_newline(depth)

                self.push_expr('break')
                self.push_newline(depth + 2)
                self.push_expr(':')
                self.push_expr(n.cond)
                self.push_expr('if not ')
                self.push_newline(depth + 1)

                self.push_expr(n.stmt)
                self.push_newline(depth + 1)
                self.push_expr('while True:')

            case c_ast.While():
                self.push_newline(depth)
                self.push_expr(n.stmt)
                self.push_newline(depth + 1)
                self.push_expr(':')
                self.push_expr(n.cond)
                self.push_expr('while ')


            case c_ast.For():
                self.push_newline(depth)

                self.push_expr(n.next)
                self.push_newline(depth + 1)

                self.push_expr(n.stmt)
                self.push_newline(depth + 1)

                self.push_expr(':')
                self.push_expr(n.cond)
                self.push_expr('while ')
                self.push_newline(depth)

                self.push_expr(n.init)
                
            case c_ast.If():
                if n.iffalse:
                    self.push_newline(depth)

                    self.push_expr(n.iffalse)
                    self.push_newline(depth + 1)

                    self.push_expr('else:')

                self.push_newline(depth)
                self.push_expr(n.iftrue)
                self.push_newline(depth + 1)

                self.push_expr(':')
                self.push_expr(n.cond)
                self.push_expr('if ')

            case c_ast.Switch():
                self.push_newline(depth)
                self.push_expr(n.stmt)
                self.push_newline(depth + 1)

                self.push_expr(':')
                self.push_expr(n.cond)
                self.push_expr('match ')

            case c_ast.Case():
                if all(not isinstance(s, c_ast.Break) for s in n.stmts):
                    print('Warning: case does not contain break statement!')

                for s in reversed(n.stmts):
                    self.push_expr(s)
                    self.push_newline(depth + 1)

                self.push_expr(':')
                self.push_expr(n.expr)
                self.push_expr('case ')

            case c_ast.Default():
                if all(not isinstance(s, c_ast.Break) for s in n.stmts):
                    print('Warning: case does not contain break statement!')

                for s in reversed(n.stmts):
                    self.push_expr(s)
                    self.push_newline(depth + 1)

                self.push_expr('case _:')


            # goto unsupported
            case c_ast.Goto():
                print('encountered goto, ignoring')
                self.push_expr('# goto ' + n.name)

            case c_ast.Label():
                self.push_expr(n.stmt)
                self.push_newline(depth)
                # label name becomes comment
                self.push_expr('# ' + n.name)


            case c_ast.BinaryOp():
                py_op = str(n.op)

                match py_op:
                    case '&&':
                        py_op = ' and '
                    case '||':
                        py_op = ' or '
                    case _:
                        py_op = py_op
                if isinstance(n.right, c_ast.BinaryOp):
                    self.push_expr(')')
                    self.push_expr(n.right)
                    self.push_expr('(')
                else:
                    self.push_expr(n.right)

                self.push_expr(py_op)

                if isinstance(n.left, c_ast.BinaryOp):
                    self.push_expr(')')
                    self.push_expr(n.left)
                    self.push_expr('(')
                else:
                    self.push_expr(n.left)

            case c_ast.UnaryOp():
                match n.op:
                    case '*':
                        self.push_expr('[0]')
                        self.push_expr(n.expr)
                    case '!':
                        self.push_expr(n.expr)
                        self.push_expr('not ')
                    case '++' | 'p++':
                        self.push_expr(' += 1 ')
                        self.push_expr(n.expr)
                    case '--' | 'p--':
                        self.push_expr(' -= 1 ')
                        self.push_expr(n.expr)
                    case  '-' | '+' | '~':
                        self.push_expr(n.expr)
                        self.push_expr(str(n.op))
                    # simulate dereference by id()
                    case  '&':
                        self.push_expr(')')
                        self.push_expr(n.expr)
                        self.push_expr('id(')
                    # simulate sizeof by .__get_sizeof__()
                    # maybe use sys.getsizeof() instead?
                    case 'sizeof':
                        self.push_expr('.__sizeof__()')
                        self.push_expr(n.expr)
                    case _:
                        print("Unknown UnaryOp", n.op)

            case c_ast.FuncCall():
                self.push_expr(')')

                if n.args:
                    self.push_expr(n.args.exprs[0])
                    for i in reversed(n.args.exprs[1:]):
                        self.push_expr(',')
                        self.push_expr(i)
                
                self.push_expr('(')
                self.push_expr(n.name.name)

            case c_ast.TernaryOp():
                #三元表达式

                self.push_expr(')')
                self.push_expr(n.iffalse)
                self.push_expr(') else (')
                self.push_expr(n.cond)
                self.push_expr(' if (')
                self.push_expr(n.iftrue)

            case c_ast.Cast():
                self.push_expr(')')
                self.push_expr(n.expr)
                self.push_expr('(')
                self.push_expr(n.to_type)

            case _:
                if n is not None:
                    print('Unknown ast type:', type(n))
                    print(str(n))
                    # if just_expr:
                    #     self.push_expr('0')
                    # else:
                    self.push_newline(depth)
                    self.push_expr('pass')

    def ast2py_one_node(self, n, just_expr=0):
        ret=''
        match n:
            case c_ast.FuncDef():
                arg_list = []
                if n.decl.type.args:
                    for i in n.decl.type.args.params:
                        arg_list.append(self.ast2py_one_node(i,1))

                ret += write_one_line(f'def {n.decl.name}(' + ', '.join(arg_list) + '):', self.m_depth)
                self.m_depth += 1
                ret += self.ast2py_one_node(n.body)
                self.m_depth -= 1
            case c_ast.Compound():
                if n.block_items and len(n.block_items) > 0:
                    for i in n.block_items:
                        ret += self.ast2py_one_node(i)
                else:
                    ret = write_one_line('pass', self.m_depth)

            case c_ast.Return():
                ret += write_one_line('return ' + self.ast2py_one_node(n.expr, 1), 1)
            case c_ast.Constant():
                py_constant = str(n.value)
                if re.match(r'^0+x', py_constant): # hex, done
                    pass
                elif re.match(r'^0', py_constant): # octal, done
                    py_constant = re.sub(r'^0+[^x]',  '0o', py_constant)

                py_constant = re.sub(r'[ULul]+$', '', py_constant)
                if len(py_constant) == 0 or py_constant == '0o':
                    py_constant = '0'
                ret = py_constant

            case c_ast.PtrDecl():
                if n.init is not None:
                    self.push_expr(n.init)
                else:
                    self.push_expr('None')
                self.push_expr(' = ')
                self.push_expr(n.name)
                self.push_newline(depth)


            case c_ast.Decl():
                if just_expr:
                    #只生成表达式，不添加缩进和换行
                    return n.name#+':' + ast_node.type.type.names.join(' ')
                else:
                    if n.init is not None:
                        ostr = n.name + ' = ' + self.ast2py_one_node(n.init, 1)
                        ret = write_one_line(ostr, self.m_depth)
                    else:
                        #add char* support
                        if isinstance(n.type, c_ast.PtrDecl) and isinstance(n.type.type, c_ast.TypeDecl) and \
                            isinstance(n.type.type.type, c_ast.IdentifierType):
                            if n.type.type.type.names ==['char']:
                                ostr =  f'{n.name} = CharPtr()'
                                self.import_file_list.append('cpp2py.cpp2py_ctype')
                                ret = write_one_line(ostr, self.m_depth)
                        elif isinstance(n.type, c_ast.ArrayDecl) and isinstance(n.type.type, c_ast.TypeDecl) and \
                            isinstance(n.type.type.type, c_ast.IdentifierType):
                            if n.type.type.type.names ==['char']:
                                ostr =  f'{n.name} = CharArray(' + self.ast2py_one_node(n.type.dim,1) +  ' )'
                                self.import_file_list.append('cpp2py.cpp2py_ctype')
                                ret = write_one_line(ostr, self.m_depth)
                        else:
                            ostr = f'{n.name} = 0'
                            ret = write_one_line(ostr, self.m_depth)
                    return ret
            case c_ast.Assignment():
                astr = self.ast2py_one_node(n.lvalue, 1)+ ' ' + n.op + ' ' + self.ast2py_one_node(n.rvalue, 1)
                if just_expr:
                    ret = astr
                else:
                    ret = write_one_line(astr, self.m_depth)
            case c_ast.ID():
                if just_expr:
                    return n.name#+':' + ast_node.
                else:
                    # ID is noop
                    return write_one_line('pass', self.m_depth)

            case c_ast.While():
                ostr = f'while {self.ast2py_one_node(n.cond, 1)}:'
                ret += write_one_line(ostr, self.m_depth)

                self.m_depth += 1
                ret += self.ast2py_one_node(n.stmt)
                self.m_depth-=1

            case c_ast.For():
                ostr = f'{n.init}'
                ret += write_one_line(ostr, self.m_depth)

                ostr = f'for {self.ast2py_one_node(n.cond, 1)}:'
                ret += write_one_line(ostr, self.m_depth)

                ostr = f'{self.ast2py_one_node(n.stmt, 1)}:'
                ret += write_one_line(ostr, self.m_depth + 1)

                ostr = f'{self.ast2py_one_node(n.next, 1)}:'
                ret += write_one_line(ostr, self.m_depth + 1)

            case c_ast.BinaryOp():
                py_op = str(n.op)

                match py_op:
                    case '&&':
                        py_op = 'and'
                    case '||':
                        py_op = 'or'
                    case _:
                        py_op = py_op
                if isinstance(n.left, c_ast.BinaryOp):
                    ret +=  '(' + self.ast2py_one_node(n.left, 1) +') ' 
                else:
                    ret +=  self.ast2py_one_node(n.left, 1)
                
                ret += py_op

                if isinstance(n.right, c_ast.BinaryOp):
                    ret += ' (' + self.ast2py_one_node(n.right, 1) + ')'
                else:
                    ret +=  self.ast2py_one_node(n.right, 1)
                
            case c_ast.If():
                ret += write_one_line( 'if ' + self.ast2py_one_node(n.cond, 1) + ":", self.m_depth)
                self.m_depth += 1
                tstr= self.ast2py_one_node(n.iftrue)
                if len(tstr)==0:
                    ret += write_one_line('pass', self.m_depth)
                else:
                    ret += tstr
                self.m_depth-=1

                ret += write_one_line( 'else:', self.m_depth)

                self.m_depth += 1
                fstr = self.ast2py_one_node(n.iffalse)
                if len(fstr)==0:
                    ret +=write_one_line( 'pass', self.m_depth)
                else:
                    ret += fstr

                self.m_depth -= 1

            case c_ast.UnaryOp():
                match n.op:
                    case '*':
                        if just_expr:
                            ret = self.ast2py_one_node(n.expr, 1) + '[0]'
                        else:
                            ret = write_one_line(self.ast2py_one_node(n.expr, 1) + '[0]', self.m_depth)
                    case '!':
                        ostr =  'not ' + self.ast2py_one_node(n.expr, 1)
                        if just_expr:
                            ret = ostr
                        else:
                            ret = write_one_line(ostr, self.m_depth)
                    case '++' | 'p++':
                        ostr = self.ast2py_one_node(n.expr, 1)+' += 1'
                        if just_expr:
                            ret = ostr
                        else:
                            ret = write_one_line(ostr, self.m_depth)
                    case '--' | 'p--':
                        ostr = self.ast2py_one_node(n.expr, 1) + ' -= 1'
                        if just_expr:
                            ret = ostr
                        else:
                            ret = write_one_line(ostr, self.m_depth)
                    case  '-' | '+' | '~':
                        ostr = str(n.op) + self.ast2py_one_node(n.expr, 1)
                        if just_expr:
                            ret = ostr
                        else:
                            ret = write_one_line(ostr, self.m_depth)
                    # simulate dereference by id()
                    case  '&':
                        ostr = 'id(' + self.ast2py_one_node(n.expr, 1) + ')'
                        if just_expr:
                            ret = ostr
                        else:
                            ret = write_one_line(ostr, self.m_depth)
                    # simulate sizeof by .__get_sizeof__()
                    # maybe use sys.getsizeof() instead?
                    case  'sizeof':
                        ostr = self.ast2py_one_node(n.expr, 1) + '.__sizeof__()'
                        if just_expr:
                            ret = ostr
                        else:
                            ret = write_one_line(ostr, self.m_depth)
                    case _:
                        print("Unknown UnaryOp", n.op)

            case c_ast.FuncCall():
                arg_list = []
                if n.args:
                    for i in n.args.exprs:
                        arg_list.append(self.ast2py_one_node(i, 1))
                call_str = n.name.name + '(' + ','.join(arg_list)  +')'
                if just_expr:
                    ret += call_str
                else:
                    ret += write_one_line(call_str, self.m_depth)
            case c_ast.TernaryOp():
                #三元表达式
                tern = '(%s if %s else %s)' % (self.ast2py_one_node(n.iftrue, 1), self.ast2py_one_node(n.cond, 1), self.ast2py_one_node(n.iffalse, 1))
                ret += write_one_line(tern, self.m_depth)

            case c_ast.Cast():
                cstr = self.ast2py_one_node(n.to_type,1) +'('+ self.ast2py_one_node(n.expr,1)      +')'
                if just_expr:
                    ret += cstr
                else:
                    ret += write_one_line(cstr, self.m_depth)
            case c_ast.Typename():
                cstr = self.ast2py_one_node(n.type,1)
                if just_expr:
                    ret += cstr
                else:
                    ret += write_one_line(cstr, self.m_depth)
            case c_ast.TypeDecl():
                cstr = self.ast2py_one_node(n.type,1)
                if just_expr:
                    ret += cstr
                else:
                    ret += write_one_line(cstr, self.m_depth)
            case c_ast.IdentifierType():
                if n.names==['long', 'long']:
                    return 'int'
            case c_ast.ArrayRef():
                ostr = self.ast2py_one_node(n.name,1) + '[0]'
                if just_expr:
                    ret += ostr
                else:
                    ret += write_one_line(ostr, self.m_depth)

            case c_ast.PtrDecl():
                #此处是指针类型转换
                #bp = sp = (int *)((int)sp + poolsz);
                ostr = self.ast2py_one_node(n.type)
                if just_expr:
                    ret += ostr
                else:
                    ret += write_one_line(ostr, self.m_depth)
            case c_ast.Break():
                ret += write_one_line('break', self.m_depth)
            case c_ast.Continue():
                ret += write_one_line('continue', self.m_depth)
            case c_ast.Goto() | c_ast.Label():
                pass
            case _:
                # switch-case unsupported
                # goto unsupported
                if n is not None:
                    print('Unknown ast type:', type(n), n)
                    if just_expr:
                        ret += '0'
                    else:
                        ret += write_one_line('pass', self.m_depth)

        return ret



# import mmap

def c2py(input_c_file, output_py_file):
    # Create the parser and ask to parse the text. parse() will throw
    # a ParseError if there's an error in the code

    text = pycparser.preprocess_file(input_c_file)

    # f = open('tmp_cprep.c','w')
    # f.write(text)
    # f.close()

    start_line=0
    parser = c_parser.CParser()
    ast = parser.parse(text, filename=input_c_file)

    f = open(output_py_file ,'w')

    # add transpiled code
    b=io.StringIO()
    a2py = Ast2Py()
    a2py.ast2py_fast(ast, b)
    py_cont = b.getvalue()

    # add required imports
    py_code = a2py.import_list()
    f.write(py_code)

    # py_cont = a2py.ast2py(ast, start_line)
    f.write(py_cont)

    # add entry point so that program can actually be run
    f.write('\n\n\n')
    f.write('if __name__ == "__main__":\n')
    f.write('\tmain()\n')


import sys

if __name__ == '__main__':
    if len(sys.argv) > 2:
        c2py(sys.argv[1],sys.argv[2])







