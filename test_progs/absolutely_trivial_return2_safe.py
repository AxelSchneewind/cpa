def f():
    return 2

def g():
    return f()

def VERIFIER_assert(cond):
    if not cond:
        reach_error()
    

def main():
    x = 1
    y = g()
    VERIFIER_assert(y == 2)
