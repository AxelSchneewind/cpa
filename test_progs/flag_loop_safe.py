def VERIFIER_assert(cond):
    if not cond:
        reach_error()
    else:
        pass
    return 

flag = 0
outer = 0
while outer < 15:
    inner = 0
    while inner < 20:
        if flag == 1:
            break              # will never execute
        inner = inner + 1
    outer = outer + 1

VERIFIER_assert(flag == 0)               # invariant holds

