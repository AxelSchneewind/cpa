def VERIFIER_assert(cond):
    if not cond:
        reach_error()
    else:
        pass
    return 

# safe_linear.py
x = 3
y = 5
z = x + y          # 8
VERIFIER_assert(z == 8)

