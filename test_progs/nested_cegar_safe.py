def VERIFIER_assert(cond):
    if not cond:
        reach_error()
    else:
        pass
    return 

def inc(x):
    return x + 1

def double_inc(x):
    return x + 2

def accumulate_safe(n):
    i = 0
    total = 0
    while i < n:
        j = 0
        inner = 0
        while j < 3:
            inner += double_inc(j)
            j = inc(j)
        total += inner
        i = inc(i)
    return total

# Trigger loop nesting and arithmetic logic
result = accumulate_safe(4)  # 4 * (2+3+4) = 4 * 9 = 36
VERIFIER_assert(result == 36)

