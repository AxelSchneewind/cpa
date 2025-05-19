n = 17             # any positive start < 1000
step = 0
while n != 1 and step < 200:   # hard bound keeps loop finite
    if n % 2 == 0:
        n = n // 2
    else:
        n = 3*n + 1
    step = step + 1

assert n == 1                  # always true under the bound

