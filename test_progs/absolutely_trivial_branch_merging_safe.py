def reach_error():
    ''' abort with error message in actual execution, is ignored by verifier '''
    print('reached error')
    exit(1)

def VERIFIER_assert(cond):
    if not cond:
        reach_error()

def main():
    ''' program entry point '''
    x = __VERIFIER_nondet_int()
    y = 0

    if x == 1:
        y = 2       # extra assignment to increase ssa index
        y = 1
    else:
        y = 1

    # always true
    VERIFIER_assert(y == 1)



if __name__ == '__main__':
    ''' entry point for actual execution '''
    main()
