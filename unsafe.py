def abort():
    pass
def reach_error():
    pass

def a():
    y = 2
    return y


def b():
    a()

def VERIFIER_assert(cond):
    if not cond:
        reach_error()
    else:
        pass
    return 


def main():
    x = 10
    y = 1
    z = 5
    while z > 1:
        y = x + y
        a()
        x += __ret
        if z % 2 == 0:
            z = z // 2
        else:
            z = 3 * z + 1
    VERIFIER_assert(False)

    b()

    c()
