def f(x):
    result = 2 * x
    return result

def VERIFIER_assert(cond):
    if not cond:
        reach_error()
    

def main():
    x = 1
    y = f(x)
    VERIFIER_assert(y != 2)