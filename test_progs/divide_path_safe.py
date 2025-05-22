# returns nondet int in [m,M]
def randint(m, M):
    result = __VERIFIER_nondet_int()
    result = result % (M + 1 - m)
    result = result + m
    return result

y = randint(-1, 1)              # {-1,0,1}
if y == 0:                      # feasible path
    exit()

x = 10 // y                     # otherwise safe (±1)
__VERIFIER_assert(x == 10 or x == -10)

