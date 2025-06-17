# Reproduction Artifcact for `Predicate Abstraction with LBE and CEGAR`

## TLDR:

Below is a brief explanation of the steps necessary to use this reproduction artifact.

1. A virtual environment within this directory is required. It can be set up using `make venv`. This target also installs mathsat into the venv.
2. Use `make prepare-benchexec benchexec-tooldef` to set up the system for benchmark execution and install the tool definition into benchexec.
3. run the demo experiment using `make run-demo-exp`. This target runs a benchmark for a variety of analyses and the tasks in `test_progs/`
4. generate the results using `make gen-demo-table`. The resulting `.html` file can be found in `results/` and can be viewed in a browser.

Running the larger experiment (`medium`) works analogously, using `make run-medium-exp` and `make gen-medium-table` in steps 3 and 4.


## Contents
This archive contains the following subdirectories and files:

- `data-submission/`: the benchmark results used in our report
    - `demo/, medium/`: subdirectories for the respective benchmarks, each with a `stats.*.table.html`
- `Makefile`: the main Makefile to set up the environment and execute benchmarks
- `pycpa/`: a CPA-implementation in python
    - it currently supports Value Analysis, Predicate Analysis (with CEGAR and ABE), Formula Analysis (Predicate Analysis with ABE that never computes abstraction), Reachability Analysis
    - only supports checking reachability of error locations
- `pycpa-tooldef.py`: A tooldefinition file for benchexec. Can be installed by placing it into the `tools/` subdirectory of the benchexec installation
- `test_progs/`: a set of manually developed verification tasks
- `benchmarks/`: contains verification tasks using python-programs based on sv-comp-tasks as well as files to generate them
    - a [submodule](benchmarks/sv-benchmarks/) containing the sv-comp tasks
    - a [subdirectory](benchmarks/ReachSafety-Combinations/) for a selected set of benchmark categories, described by a `.set` file
    - a [Makefile](benchmarks/Makefile) for generating the benchmark sets
    - a [benchset.mk](benchmarks/benchset.mk)-Makefile defining the transpilation process for a single benchmark set. To be called by the `Makefile`
    - a [sed-script](benchmarks/prepare_c.txt) for preparing svbenchmark files for transpilation 
    - a [script](benchmarks/transpile.sh) for transpiling the program of a given verification task to python
    - a [python-program](benchmarks/c2py) for transpiling the program of a given verification task to python, based on [cpp2py](https://pypi.org/project/cpp2py/)
- `bench-defs/`: benchmark definitions
    - a small  benchmark set (`pycpa-demo.xml`) using our `test_progs`
    - a larger benchmark set (`pycpa-medium.xml`) using python programs generated from sv-comp tasks
- `requirements`: dependencies for the virtual environment


## Required Software

- `python:3.11` (required)
- `gcc` (required)
- `wget` (if mathsat should be installed automatically)
- `mathsat-5.6.11` (can automatically be installed into venv using `make install-msat`)
- python libraries specified in `requirements.txt`  (automatically installed into venv using `make venv`)


## Virtual Environment

The `Makefiles` to run experiments assumes that a virtual environment is enabled where the 
[prerequisites](requirements.txt) and `mathsat` are installed.

Further, the benchexec installation must contain the [tooldefinition file](pycpa-tooldef.py) at `tools/pycpa.py`.

This virtual environment can be set up using
```sh
make venv
```
This target first sets up the virtual environment at `./venv`.
Then it automatically downloads the source code for mathsat into this directory if not present already,
compiles and installs it into the venv.
This step requires `wget` to be installed.
 Alternatively, the source code can be 
placed at `mathsat-5.6.11-linux-x86_64.tar.gz` and 
installed using `make install-mathsat`


## Generating Benchmarks
The `svcomp23` benchmark set is provided as a submodule in [`benchmarks/sv-benchmarks`](benchmarks/sv-benchmarks).
The provided benchmark sets can transpiled to python programs using
```sh
make all
```
from within the `benchmarks/` directory.
Note that this can take up to 3h for the selected benchmark sets.
A summary of the transpilation results can be viewed using
```sh
make stats
```

To generate an individual task set, use e.g.
```sh
make ReachSafety-BitVectors.generate
make ReachSafety-BitVectors.stats
```


## Defining Benchmark Sets
Benchmark sets are provided in `bench-defs/`.
This archive includes `pycpa-demo` and `pycpa-medium` benchmarks, defined in their respective `.xml` files.

The corresponding tasks are specified in the `bench-defs/sets/` subdirectory.


### Adding a Benchmark set
A new set of benchmarks can be added by defining a set file `bench-defs/sets/benchmark.set`  
containing relative paths to the tasks `.yml` files.
If such files have to be generated, see the [Generating Benchmarks](#generating-benchmarks) section.

Benchmarks can then be defined by adding a `pycpa-benchmark.xml` file to `bench-defs/` 
(keeping the `pycpa` prefix for usage with the makefile).
Analogously to `pycpa-medium`, the run configurations and benchmark sets can be defined
in this file.

Then, the benchmarks can be executed and visualized using 
```sh
make run-benchmark-exp
make gen-benchmark-table
```


## Running Benchmarks
The benchmarks from the report can be exeuted using their respective `run-*-exp` targets.

Additionally, the makefile can be used to run analysis on the test programs
without benchexec. 
This can be done using 
```sh
make run-examples
``` 
which runs all available configurations.
To run a specific configuration `C`, use `make run-examples-C`.

These targets can also be used to get the command to execute the analysis
manually.
