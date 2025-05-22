def abort():
    pass
def reach_error():
    pass

def VERIFIER_assert(cond):
    if not cond:
        reach_error()
    else:
        pass
    return 

def f(x):
    return 2 * x

def g(x):
    result = 2 * x
    return result

def h(x):
    return g(x)

def main():
    x = 4

    y = h(g(h(x)))
    z = g(h(g(x)))

    VERIFIER_assert(y == z)
    VERIFIER_assert(y == 32)

main()
