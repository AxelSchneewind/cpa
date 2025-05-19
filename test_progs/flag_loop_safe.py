flag = 0
outer = 0
while outer < 15:
    inner = 0
    while inner < 20:
        if flag == 1:
            break              # will never execute
        inner = inner + 1
    outer = outer + 1

assert flag == 0               # invariant holds

