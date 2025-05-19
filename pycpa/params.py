#!/usr/bin/env python3
"""
Command-line interface shared by all pycpa entry points.
"""

import argparse

# --------------------------------------------------------------------------- #
#  Core parser                                                                #
# --------------------------------------------------------------------------- #
parser = argparse.ArgumentParser(
    prog        = "pycpa",
    description = "Predicate Abstraction, Value Analysis, and other CPAs "
                  "for Python/C benchmarks",
)

# --------------------------------------------------------------------------- #
#  Positional: program(s)                                                     #
# --------------------------------------------------------------------------- #
parser.add_argument(
    "program",
    nargs="+",
    help="one or more .py files to verify",
)

# --------------------------------------------------------------------------- #
#  Mandatory analysis / property choices                                      #
# --------------------------------------------------------------------------- #
parser.add_argument(
    "-c", "--config",
    action   = "append",
    required = True,
    metavar  = "CPA",
    help     = "analysis configuration to use "
               "(repeat for multiple CPAs; see --list-configs)",
)
parser.add_argument(
    "-p", "--property",
    action   = "append",
    required = True,
    metavar  = "SPEC",
    help     = "property to check "
               "(repeat for multiple specs; see --list-properties)",
)

# --------------------------------------------------------------------------- #
#  Optional listings                                                          #
# --------------------------------------------------------------------------- #
parser.add_argument(
    "--list-configs",
    action = "store_true",
    help   = "print available analysis configurations and exit",
)
parser.add_argument(
    "--list-properties",
    action = "store_true",
    help   = "print available specification modules and exit",
)

# --------------------------------------------------------------------------- #
#  Runtime knobs                                                              #
# --------------------------------------------------------------------------- #
parser.add_argument(
    "--max-iterations",
    type    = int,
    default = 50_000,
    metavar = "N",
    help    = "ARG node budget per run / CEGAR round (default: 50 000)",
)
parser.add_argument(
    "--verbose",
    action = "store_true",
    help   = "print each new predicate set and CEGAR round progress",
)
