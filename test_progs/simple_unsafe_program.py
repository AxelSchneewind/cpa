def VERIFIER_assert(cond):
    if not cond:
        reach_error()
    else:
        pass
    return

def inc(x):
    return x + 1

def buggy_operation(x):
    return x + 2

def simple_unsafe_program(n):
    i = 0
    result = 0
    while i < n:
        result = buggy_operation(result)
        i = inc(i)
    return result

num_iterations = 3
final_val = simple_unsafe_program(num_iterations)
VERIFIER_assert(final_val == num_iterations)
