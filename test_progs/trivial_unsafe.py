def abort():
    pass
def reach_error():
    pass

def VERIFIER_assert(cond):
    if not cond:
        reach_error()
    else:
        pass
    return 



def main():
    x = 1
    VERIFIER_assert(False)


main()
