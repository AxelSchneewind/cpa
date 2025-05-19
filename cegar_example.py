# example_cegar.py

# Model a nondet choice; we don't actually execute it, just for CFA building
def nondet():
    pass

# Error‐reporting hook for the verifier CPA
def reach_error():
    pass

def VERIFIER_assert(cond):
    if not cond:
        reach_error()
    return

def main():
    # l0
    x = nondet()
    # branch [x < 10]
    if x < 10:
        # l2→l3
        x = x + 1
    # at l3: check that we never reach x == 20
    VERIFIER_assert(x != 20)

if __name__ == "__main__":
    main()

