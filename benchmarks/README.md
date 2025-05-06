# Benchmark Generation

This directory contains scripts to generate benchmark programs in python.

## Setup

Clone [sv-benchmarks](https://gitlab.com/sosy-lab/benchmarking/sv-benchmarks.git) into this directory (TODO: add as submodule).

The virtual environment for python has to be set up by using the Makefile from the base directory.

## Generating benchmarks

Simply use
```sh
./transform-set.sh bitvector.set
```
to generate python files from the c files corresponding to the example set.
