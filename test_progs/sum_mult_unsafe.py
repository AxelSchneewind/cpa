def mult(x, y):
    return x * (y + 1)  # BUG: uses y+1

def sum_mult(n):
    total = 0
    i = 1
    while i < 1, n+1:
        j = 1
        while j < i+1:
            total += mult(i, j)
            j += 1
        i += 1
    return total

result = sum_mult(4)
# Actual is 95, but we assert 65
if result != 65:
    reach_error()

