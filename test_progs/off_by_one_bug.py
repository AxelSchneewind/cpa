size = 10
idx  = 0
while idx <= size:     # off-by-one: should be <
    if idx == size:
        reach_error()  # idx reaches 10 → bug
    idx = idx + 1

