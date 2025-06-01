def reach_error():
    ''' abort with error message in actual execution, is ignored by verifier '''
    print('reached error')
    exit(1)

def VERIFIER_assert(cond):
    if not cond:
        reach_error()

def main():
    ''' program entry point '''
    VERIFIER_assert(False)



if __name__ == '__main__':
    ''' entry point for actual execution '''
    main()
