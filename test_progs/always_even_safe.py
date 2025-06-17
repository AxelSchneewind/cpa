def reach_error():
    ''' abort with error message in actual execution, is ignored by verifier '''
    print('reached error')
    exit(1)

def VERIFIER_assert(cond):
    if not cond:
        reach_error()

def main():
    ''' program entry point '''
    n = __VERIFIER_nondet_int()
    n = n % 10

    x = 0
    i = 0
    while i < n:
        x += 2
        i += 1

    VERIFIER_assert((x % 2) == 0)


if __name__ == '__main__':
    ''' entry point for actual execution '''
    main()
