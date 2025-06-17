# pycpa

A configurable program analysis tool implemented in python.
Intended to be usable in a similar way to [cpachecker](https://gitlab.com/sosy-lab/software/cpachecker).


## Usage:
The tool can be executed using
```
python -m pycpa
```
See
```
python -m pycpa -h
```
For available parameters and flags.


## Code Structure
The repository contains the following files and subdirectories.

- `__main__.py`: the main entrypoint for this module
- `ast/`, `preprocessor.py`: define transformations to perform on the AST such that it can be represented as a CFA
- `cfa.py`: defines control flow automata, instructions and an ast visitor that computes a CFA
- `cpa.py`: defines base classes for CPA, TransferRelation, MergeOperator, StopOperator
- `analyses/`: contains the CPA definitions and helpers for different analyses:
    - Generic: `ARGCPA, CompositeCPA, StackCPA` to wrap other cpas
    - `LocationCPA` to represent program location
    - `PropertyCPA` to represent reach-safety
    - `ValueAnalysis`: CPA for constant propagation
    - `PredAbs[ABE]CPA`: CPA for predicate abstraction
    - `PropertyPrecision`: for representing precision (location-based)
    - `PropertyABEPrecision`: contains operators for block-head-checks
    - `PredAbsCEGAR`: CEGAR algorithm class for predicate abstraction
    - Helpers: 
        - `cegar_helper.py`: for feasibility checks and precision refinement
        - `ssa_helper.py`: for manipulating SSA formulas
- `config/`, `configs.py`: specifies analysis configurations
    - to add an analysis `A`, add `A.py` to `config/` and define either
        - the `get_algorithm` function, that returns an algorithm object
        - the `get_cpas` function, that returns a list of CPAs to use
    - analysis can then be used by passing `-c A`
    
