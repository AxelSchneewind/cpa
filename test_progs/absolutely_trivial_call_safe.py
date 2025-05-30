def VERIFIER_assert(cond):
    if not cond:
        reach_error()
    return
    

def main():
    x = 1
    VERIFIER_assert(x == 1)
