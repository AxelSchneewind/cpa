# coding:utf-8
import copy
import os.path

from .read_one_file import read_one_file


def read_one_c_file(file_name):

    pass



def read_funtion_def(file_name):
    """
    查找函数定义
    :param file_name:
    :return:
    """
    function_str_list = []
    txt = read_one_file(file_name)

    is_find_until_block_coment_end = 0  # 判断是否在块注释中
    in_block = 0  # 判断是否在大括号中
    lines = txt.split('\n')
    for index, i in enumerate(lines):
        i = i.strip()
        if len(i) < 1:
            #去除空行
            continue

        if i.find('{') >= 0:
            #大括号处理
            in_block += 1
        if i.find('}') >= 0:
            in_block -= 1
            continue

        if in_block > 0:
            #在大括号中，不处理
            continue

        if i[0] == '/' and i[1] == '/':
            #单行注释，不处理
            continue
        if i[0] == '/' and i[1] == '*':
            #多行注释，不处理
            is_find_until_block_coment_end = 1

        if is_find_until_block_coment_end:
            #多行注释，查找结束符
            # 查找到 */ 则结束否则一直认为是在注释中
            if i.find('*/') >= 0:
                is_find_until_block_coment_end = 0
                continue
            continue

        if i.find('(')==-1:
            #没有小括号，不是函数定义？
            continue
        if i.find(')')==-1:
            #没有右括号，认为下一行和这一行需要连在一起？？？
            inext= lines[index+1]
            if inext.find(('{'))!=-1:
                inext = inext[0:inext.find(('{'))]

            i=i+inext


        function_str_list.append(i)

    return function_str_list



def parse_param_list(param_str_list):
    """

    :param param_str_list: ['unsigned char *axis', ' unsigned short int rwcom', ' unsigned int data']
    :return:
    """
    param_list = []
    for i in param_str_list:
        curr_param_list = i.split(' ')
        while '' in curr_param_list:
            curr_param_list.remove('')
        if len(curr_param_list)==0:
            # i 是空数组，
            continue

        while (len(curr_param_list[-1])>0) and (curr_param_list[-1][0]=='*'):
            # 处理指针-20221001
            curr_param_list.insert(-1, '*')
            curr_param_list[-1]=curr_param_list[-1][1:]

        param_name = curr_param_list[-1]
        param_type = curr_param_list[0:-1]
        param_list.append((param_name, param_type))

    return param_list


def function_parse(function_str_list):
    """
    返回函数列表
    :param function_str_list:
    :return:[{'func_name': 'ETH6045_sd_stop', 'ret_type': ['void'], 'param': [('Chip_Axis', ['unsigned', 'int'])]},....]
    """
    function_list = []
    for i in function_str_list:
        if len(i.split('('))<2:
            continue
        head, param = i.split('(')
        head_list = head.split(' ')
        while '' in head_list:
            head_list.remove('')
        function_name = head_list[-1]
        function_ret_type = head_list[0:-1]
        param = param.split(')')[0]
        param_str_list = param.split(',')
        param_list = parse_param_list(param_str_list)
        function_list.append({'func_name': function_name, 'ret_type': function_ret_type, 'param': param_list})

    return function_list

def get_one_type_size(type_list):
    if len(type_list) == 0:
        return 0

    if is_type_ptr(type_list):
        # for 32bit system. pointer is always 4byte
        return 4
    if len(type_list) == 1:
        if type_list[0] == 'void':
            return 0
        elif type_list[0] == 'char':
            return 1
        elif type_list[0] == 'short':
            return 2
        elif type_list[0] == 'int':
            return 4
        elif type_list[0] == 'int32_t':
            return 4
        elif type_list[0] == 'uint32_t':
            return 4
        elif type_list[0] == 'unsigned':
            return 4
        elif type_list[0] == 'double':
            return 8
    elif len(type_list) == 2:
        if type_list[0] == 'unsigned' and type_list[1] == 'char':
            return 1
        elif type_list[0] == 'unsigned' and type_list[1] == 'short':
            return 2
        elif type_list[0] == 'unsigned' and type_list[1] == 'int':
            return 4
    elif len(type_list) == 3:
        if type_list[1] == 'short' and type_list[2] == 'int':
            return 2
        elif type_list[1] == 'unsigned' and type_list[2] == 'int':
            return 4
    print('unknown type_size:', type_list)
    return -1
def is_type_ptr(type_list):
    for i in type_list:
        if i=='*':
            return True
    return False


def get_ptr_inner_type(type_list):
    """

    :param type_list: [unsigned int *]
    :return: [unsigned int]
    """
    type_list = copy.deepcopy(type_list)

    while (len(type_list) > 0) and (type_list[-1] == '*'):
        del type_list[-1]
    return type_list

def get_one_ptr_inner_size(type_list):
    type_list = get_ptr_inner_type(type_list)
    return get_one_type_size(type_list)