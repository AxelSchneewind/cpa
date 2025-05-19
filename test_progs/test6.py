# func_loop_bug.py
def dec(x):
    return x - 1

n = 3
while n >= 0:
    if n == 0:
        reach_error()  # reachable on last iteration
    n = dec(n)

