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
    y = 1
    z = 5       # sequence reaches 1:  5 -> 16 -> 8 -> 4 -> 2 -> 1
                # therefore, program terminates
    while z > 1:
        y = x + y
        x += 2
        if z % 2 == 0:
            z = z // 2
        else:
            z = 3 * z + 1

    VERIFIER_assert(x == 10)
main()
