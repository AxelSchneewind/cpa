def VERIFIER_assert(cond):
    if not cond:
        reach_error()
    else:
        pass
    return 

x = 0
for outer in range(3):           # fixed 3 iterations
    y = randint(0, 10)           # treated as nondet
    while y > 0:
        y = y - 1
        x = x + 1

VERIFIER_assert(x < 0)       # always false → bug reachable

