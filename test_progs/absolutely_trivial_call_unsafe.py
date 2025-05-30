def VERIFIER_assert(cond):
    if not cond:
        reach_error()
    

def main():
    x = 1
    VERIFIER_assert(x != 1)