def mult(x, y):
    return x * y

def sum_mult(n):
    total = 0
    i = 1
    while i < n+1:
        while j < i+1:
            total += mult(i, j)
            j += 1
        i += 1
    return total

result = sum_mult(4)
# 1 + (2+4) + (3+6+9) + (4+8+12+16) = 65
if result != 65:
    reach_error()

