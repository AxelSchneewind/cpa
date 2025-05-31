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
    x = 0
    z = 5       # sequence reaches 1:  5 -> 16 -> 8 -> 4 -> 2 -> 1
                # therefore, program terminates
    while z > 1:
        x += 1
        if z % 2 == 0:
            z = z // 2
        else:
            z = 3 * z + 1

    VERIFIER_assert(x == 5)
main()
