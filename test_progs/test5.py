# unsafe_nested.py
from random import randint

x = 0
for outer in range(3):           # fixed 3 iterations
    y = randint(0, 10)           # treated as nondet
    while y > 0:
        y = y - 1
        x = x + 1

assert x < 0        # always false → bug reachable

