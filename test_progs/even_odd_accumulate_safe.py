def inc(x):
    return x + 1

def accumulate(n, m):
    i = 0
    total = 0
    while i < n:
        j = 0
        while j < m:
            if (i + j) % 2 == 0:
                total += i * j
            else:
                total += i + j
            j = inc(j)
        i = inc(i)
    return total

result = accumulate(3, 4)
# Hand-computed: 24
if result != 24:
    raise Exception(f"Wrong: got {result}, expected 24")

