def inc(x):
    return x + 1

def buggy_double_inc(x):
    return x + 3  # Bug: +3 instead of +2

def accumulate_unsafe(n):
    i = 0
    total = 0
    while i < n:
        j = 0
        inner = 0
        while j < 3:
            inner += buggy_double_inc(j)
            j = inc(j)
        total += inner
        i = inc(i)
    return total

# Should be 4 * (2+4+6) = 48
# But becomes 4 * (3+5+7) = 60 → assertion should FAIL
result = accumulate_unsafe(4)
assert result == 48

