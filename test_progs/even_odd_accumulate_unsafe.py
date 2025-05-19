def inc(x):
    return x + 1

def accumulate_buggy(n, m):
    i = 0
    total = 0
    while i < n:
        j = 0
        while j < m:
            # BUG: both branches use i*j
            if (i + j) % 2 == 0:
                total += i * j
            else:
                total += i * j
            j = inc(j)
        i = inc(i)
    return total

result = accumulate_buggy(3, 4)
# Wrong actual: 18, but we assert 24
if result != 24:
    raise Exception(f"Wrong: got {result}, expected 24")

