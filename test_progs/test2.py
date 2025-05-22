def VERIFIER_assert(cond):
    if not cond:
        reach_error()
    else:
        pass
    return 

# safe_counter.py
i = 0
limit = 7
while i < limit:   # executes exactly 7 times
    i = i + 1

VERIFIER_assert(i == 7)

