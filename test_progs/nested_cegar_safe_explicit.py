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

result = accumulate_safe(4)  # Should be 4 * (2 + 4 + 6) = 48
if result != 48:
    reach_error()

