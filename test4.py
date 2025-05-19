# unsafe_modulo.py
       # our analyser treats this as an error edge

x = 17
if (x % 2) == 1:          # 17 is odd → true-branch taken
    reach_error()

# else‐branch unreachable but included so the CFA has an assumption edge

