def inc(x):
    return x + 1

def add(x, y):
    return x + y

def sum_cubes(n):
    s = 0
    i = 0
    while i < n:
        j = 0
        while j < n:
            k = 0
            while k < n:
                s += add(i, add(j, k))
                k = inc(k)
            j = inc(j)
        i = inc(i)
    return s

result = sum_cubes(3)
# Sum over 0≤i,j,k<3 of (i+j+k) = 81
if result != 81:
    reach_error()

