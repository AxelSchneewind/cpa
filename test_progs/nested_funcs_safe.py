def VERIFIER_assert(cond):
    if not cond:
        reach_error()
    else:
        pass
    return 

def incr(x):          # first user function
    return x + 1

def sum_to(n):        # second function: Σ_{i=0}^{n-1} i
    s = 0
    i = 0
    while i < n:
        s = s + i
        i = incr(i)
    return s

total = sum_to(5)     # 0+1+2+3+4 = 10
VERIFIER_assert(total == 10)

