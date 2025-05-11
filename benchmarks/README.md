# Benchmark Generation

This directory contains scripts to generate benchmark programs in python.

## Setup

The virtual environment for python has to be set up by using the Makefile from the base directory.

The sv-benchmark submodule has to be made available.

## Generating benchmarks

Simply use
```sh
./transpile-set.sh ReachSafety-Loops.set
```
to generate python files from the c files corresponding to the example set.

