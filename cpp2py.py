# taken from https://pypi.org/project/cpp2py/ with small fixes applied

#from .cparselite import read_funtion_def
from pycparser import c_parser
from pycparser import c_ast
import pcpp
import io

def write_one_line(buf, depth):
    return '\t'*depth + buf + '\n'

def cpp_parse(text, input_c_file):
    """
    解析include，并生成import
    """
    ret = ''
    py_code=''
    line_no = 0
    in_comment = 0
    for one_line in text.split('\n'):

        line_no+=1
        one_line = one_line.strip()
        if in_comment:
            if '*/' in one_line:
                #注释结束
                if one_line[-2:]!='/*':
                    print('WARNING: comment in middle may losing code\n', one_line)
                in_comment=0
            #ret += '# '+ one_line +'\n'
            ret +='\n'
            continue

        if one_line[:2]=='//':
            #comment one line

            #ret +='# '+ one_line[2:] +  '\n'
            ret +='\n'
            continue


        if one_line[:2]=='/*':
            #comment one line
            ret +='\n'
            in_comment=1
            continue


        inc = '#include'
        if one_line[:len(inc)]==inc:
            inc_file = one_line[len(inc):]
            inc_file=inc_file.replace('"','').replace('<','').replace('>','').replace('.h','').replace('.hpp','').strip()
            py_code+= 'import '+inc_file+'\n'
            ret +='\n'
            continue

        ret += one_line+'\n'

    return ret,py_code


class Ast2Py:
    def __init__(self):
        self.m_depth = 0
        self.import_file_list=[]
    def import_list(self):
        ret = ''
        self.import_file_list = list(set(self.import_file_list))
        for i in self.import_file_list:
            ret += 'from '+i+' import *\n'
        return ret

    def ast2py(self, ast,start_line=0):
        ret = ''
        for i in ast.ext:
            ret +=self.ast2py_one_node(i)
        return ret

    def ast2py_one_node(self, n, just_expr=0):
        ret=''
        if isinstance(n, c_ast.FuncDef):
            arg_list = []
            if n.decl.type.args:
                for i in n.decl.type.args.params:
                    arg_list.append(self.ast2py_one_node(i,1))

            ret += write_one_line('def ' + n.decl.name + '(' + ', '.join(arg_list) + '):', self.m_depth)
            self.m_depth += 1
            ret += self.ast2py_one_node(n.body)
            self.m_depth -= 1
        elif isinstance(n, c_ast.Compound):
            if n.block_items and len(n.block_items) > 0:
                for i in n.block_items:
                    ret += self.ast2py_one_node(i)
            else:
                ret += write_one_line('pass', self.m_depth)

        elif isinstance(n, c_ast.Return):
            ret += write_one_line('return ' + self.ast2py_one_node(n.expr), self.m_depth)
        elif isinstance(n, c_ast.Constant):
            return str(n.value)
        elif isinstance(n, c_ast.Decl):
            if just_expr:
                #只生成表达式，不添加缩进和换行
                return n.name#+':' + ast_node.type.type.names.join(' ')
            else:

                if n.init is not None:
                    ostr = n.name + ' = ' + self.ast2py_one_node(n.init, 1)
                    ret += write_one_line(ostr, self.m_depth)
                else:
                    #add char* support
                    if isinstance(n.type, c_ast.PtrDecl) and isinstance(n.type.type, c_ast.TypeDecl) and \
                        isinstance(n.type.type.type, c_ast.IdentifierType):
                        if n.type.type.type.names ==['char']:
                            ostr =  n.name + ' = CharPtr()'
                            self.import_file_list.append('cpp2py.cpp2py_ctype')
                            ret += write_one_line(ostr, self.m_depth)
                    elif isinstance(n.type, c_ast.ArrayDecl) and isinstance(n.type.type, c_ast.TypeDecl) and \
                        isinstance(n.type.type.type, c_ast.IdentifierType):
                        if n.type.type.type.names ==['char']:
                            ostr =  n.name + ' = CharArray('+self.ast2py_one_node(n.type.dim,1)    +  ' )'
                            self.import_file_list.append('cpp2py.cpp2py_ctype')
                            ret += write_one_line(ostr, self.m_depth)


                return ret
        elif isinstance(n, c_ast.Assignment):
            astr = self.ast2py_one_node(n.lvalue,1)+ ' ' + n.op + ' ' + self.ast2py_one_node(n.rvalue, 1)
            if just_expr:
                ret += astr
            else:
                ret += write_one_line(astr, self.m_depth)
        elif isinstance(n, c_ast.ID):
            if just_expr:
                return n.name#+':' + ast_node.
            else:
                return 'ID COULD NOT BE A LINE\n'


        elif isinstance(n, c_ast.While):
            ostr = 'while ' + self.ast2py_one_node(n.cond, 1) + ":"
            ret += write_one_line(ostr, self.m_depth)
            self.m_depth += 1
            ret += self.ast2py_one_node(n.stmt)
            self.m_depth-=1
        elif isinstance(n, c_ast.If):
            ret += write_one_line( 'if ' + self.ast2py_one_node(n.cond, 1) + ":", self.m_depth)
            self.m_depth += 1
            tstr= self.ast2py_one_node(n.iftrue)
            if len(tstr)==0:
                ret += write_one_line( 'pass', self.m_depth)
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

        elif isinstance(n, c_ast.UnaryOp):
            if n.op== '*':
                if just_expr:
                    ret += self.ast2py_one_node(n.expr, 1) + '[0]'
                else:
                    ret +=write_one_line(self.ast2py_one_node(n.expr, 1) + '[0]', self.m_depth)
            elif n.op== '!':
                ostr =  'not '+ self.ast2py_one_node(n.expr, 1)
                if just_expr:
                    ret += ostr
                else:
                    ret +=write_one_line(ostr, self.m_depth)
            elif n.op== '++':
                ostr = self.ast2py_one_node(n.expr, 1)+' +=1'
                if just_expr:
                    ret += ostr
                else:
                    ret +=write_one_line(ostr, self.m_depth)
            elif n.op== '--':
                ostr = self.ast2py_one_node(n.expr, 1)+' -=1'
                if just_expr:
                    ret += ostr
                else:
                    ret +=write_one_line(ostr, self.m_depth)
            else:
                print("Unknown UnaryOp", n.op)

        elif isinstance(n, c_ast.BinaryOp):
            bstr = self.ast2py_one_node(n.left, 1) + n.op + self.ast2py_one_node(n.right, 1)
            if just_expr:
                ret += bstr
            else:
                ret += write_one_line(bstr, self.m_depth)
            #if n.op=='==' or n.op=='-' or n.op=='+' or n.op=='*' or n.op=='/' or n.op=='<' or n.op=='<=' or n.op=='>=' or n.op=='||':
            #else:
            #    print('unknown binaryoperator')
        elif isinstance(n, c_ast.FuncCall):
            arg_list = []
            if n.args:
                for i in n.args.exprs:
                    arg_list.append(self.ast2py_one_node(i, 1))
            call_str = n.name.name + '(' + ','.join(arg_list)  +')'
            if just_expr:
                ret += call_str
            else:
                ret += write_one_line(call_str, self.m_depth)
        elif isinstance(n, c_ast.TernaryOp):
            #三元表达式
            tstr = 'if ' + self.ast2py_one_node(n.cond,1) + ' then ' + self.ast2py_one_node(n.iftrue,1) +' else ' + self.ast2py_one_node(n.iffalse,1)
            ret += tstr

        elif isinstance(n, c_ast.Cast):
            cstr = self.ast2py_one_node(n.to_type,1) +'('+ self.ast2py_one_node(n.expr,1)      +')'
            if just_expr:
                ret += cstr
            else:
                ret += write_one_line(cstr, self.m_depth)
        elif isinstance(n, c_ast.Typename):
            cstr = self.ast2py_one_node(n.type,1)
            if just_expr:
                ret += cstr
            else:
                ret += write_one_line(cstr, self.m_depth)
        elif isinstance(n, c_ast.TypeDecl):
            cstr = self.ast2py_one_node(n.type,1)
            if just_expr:
                ret += cstr
            else:
                ret += write_one_line(cstr, self.m_depth)
        elif isinstance(n, c_ast.IdentifierType):
            if n.names==['long', 'long']:
                return 'int'
        elif isinstance(n, c_ast.ArrayRef):
            ostr = self.ast2py_one_node(n.name,1) + '[0]'
            if just_expr:
                ret += ostr
            else:
                ret += write_one_line(ostr, self.m_depth)

        elif isinstance(n, c_ast.PtrDecl):
            #此处是指针类型转换
            #bp = sp = (int *)((int)sp + poolsz);
            ostr = self.ast2py_one_node(n.type)
            if just_expr:
                ret += ostr
            else:
                ret += write_one_line(ostr, self.m_depth)
        else:
            print('Unknown ast type:', type(n))
            # print('Unknown',ast_node)


        return ret



def c2py(input_c_file, output_py_file):
    # Create the parser and ask to parse the text. parse() will throw
    # a ParseError if there's an error in the code
    #
    parser = c_parser.CParser()
    a2py = Ast2Py()

    f = open(input_c_file, 'r')
    text = f.read()
    f.close()
    
    
    #预处理
    #text, py_code = cpp_parse(text, input_c_file)

    prep = pcpp.Preprocessor()
    prep.parse(text,input_c_file,{} )
    b=io.StringIO()
    prep.write(b)
    text = b.getvalue()
    py_code =''



    f=open('tmp_cprep.c','w')
    f.write(text)
    f.close()

    start_line=0
    ast = parser.parse(text, filename=input_c_file)
    py_cont = a2py.ast2py(ast, start_line)
    py_code = a2py.import_list()
    f=open(output_py_file,'w')

    f.write(py_code)
    f.write(py_cont)
    f.close()


if __name__ == '__main__':
    c2py('c2.c','c2.py')







