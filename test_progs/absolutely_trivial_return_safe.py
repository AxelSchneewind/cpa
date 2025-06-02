def f():
    return 2

def VERIFIER_assert(cond):
    if not cond:
        reach_error()
    

def main():
    x = 1
    y = f()
    VERIFIER_assert(y == 2)
