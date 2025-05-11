# pycpa


## Contents

- transpilation from c to python:
    - a fixed [source file](cpp2py.py) for `cpp2py` is provided
    - a [script](benchmarks/prepare_c.sh) for preparing svbenchmark files for transpilation 
    - a [script](benchmarks/transpile_set.sh) for transpiling the programs of a given set of verification tasks to python programs
- an implementation of CPA in `pycpa` 
    - it currently supports Value-Analysis, BMC
    - it supports checking ReachSafety


## Generating Benchmarks
The `svcomp23` benchmark set is provided as a submodule in [`benchmarks/`](benchmarks/).
The benchmark sets can be extracted and transpiled to python programs using
```sh
make generate-benchmarks
```
Note that this can take up to 6h for the selected benchmark sets.

To generate an indiviual task set, use e.g.
```sh
make benchmarks/ReachSafety-Floats
```

## Running Benchmarks
The benchmark programs can be verified by running
```sh
make run-benchmarks
```
