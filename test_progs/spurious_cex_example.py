# File: spurious_cex_example_v2.py

def reach_error():
    # This function is a marker for an error state.
    pass

def VERIFIER_assert(cond):
    # A simple assertion function.
    if not cond:
        reach_error()
    return

def main():
    x = 1 
    y = 0 
    
    if x > 0: # True, since x = 1
        y = 5   # y becomes 5
    else:
        y = 10  # This branch is not taken
        
    # Concretely, at this point, y MUST be 5.
    
    # Introduce a simple loop.
    # The purpose here is to create a merge point (loop head) where,
    # if the precision is not strong enough to prove y=5 as an invariant
    # or carry it through the merge, the information might be lost.
    k = 0
    while k < 1: # Loop executes exactly once
        # This loop does not modify y.
        # some_other_var = x + k # example of an operation inside loop
        k = k + 1
        
    # After the loop:
    # Concretely, y is still 5.
    # Abstractly, if the loop analysis "weakened" the knowledge about y,
    # the state might allow y to be something other than 5.
    
    if y == 10: 
        # This condition should still be concretely false (y is 5).
        # If the CEGAR loop is triggered, it means the abstract analysis
        # (before refinement) thought this path was possible.
        VERIFIER_assert(False) 
    
    return

# Standard way to call main if this script is run directly.
if __name__ == '__main__':
    main()

