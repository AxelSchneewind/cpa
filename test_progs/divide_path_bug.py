from random import randint      # nondet int

y = randint(-1, 1)              # {-1,0,1}
if y == 0:                      # feasible path
    reach_error()

x = 10 // y                     # otherwise safe (±1)
assert x in (-10, 10)

