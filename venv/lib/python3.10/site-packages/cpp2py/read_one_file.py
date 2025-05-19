#coding:utf-8

def read_one_file(file_name):
    try:
        f = open(file_name, 'r', encoding='utf-8')
        txt = f.read()
        f.close()
        return txt
    except Exception as e:
        print('utf-8 decode error. try gbk')
        f = open(file_name, 'r', encoding='GB18030')
        txt = f.read()
        f.close()
        return txt

    return None