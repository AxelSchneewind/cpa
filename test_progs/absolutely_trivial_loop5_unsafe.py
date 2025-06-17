def __VERIFIER_assert(cond):
    if not cond:
        reach_error()
    return

def main():
    i = 0
    while i < 5:
        __VERIFIER_assert(i <= 4) 
        i+=1

    __VERIFIER_assert(i != 5) 
