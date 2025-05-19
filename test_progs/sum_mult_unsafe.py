def mult(x, y):
    return x * (y + 1)  # BUG: uses y+1

def sum_mult(n):
    total = 0
    for i in range(1, n+1):
        for j in range(1, i+1):
            total += mult(i, j)
    return total

result = sum_mult(4)
# Actual is 95, but we assert 65
if result != 65:
    raise Exception(f"Wrong: got {result}, expected 65")

