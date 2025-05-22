

# venv is required for benchmark generation
venv:
	@echo 'setting up the virtual environment'
	python -m venv venv
	./venv/bin/pip install -r requirements.txt
	@echo 'use '
	@echo '  source venv/bin/activate'
	@echo 'to activate'

check-venv:
	@[ ! -z "$(VIRTUAL_ENV)" ] || (echo 'activate the virtual environment first using source venv/bin/activate' && exit 1)

# the cpp2py required for benchmark generation seems to be abandoned and has bugs
# use this target to use a (partially) fixed version supplied here
# Note: this still does not support e.g. goto
.phony: path-cpp2py
patch-cpp2py: cpp2py.py
	@echo 'patching cpp2py'
	@cp cpp2py.py ./venv/lib/python3.13/site-packages/cpp2py/cpp2py.py


# helper targets for benchmark generation
benchmarks/%.set:
	@echo 'converting c benchmarks to python'
	@make -C benchmarks $*.set 

benchmarks/%: benchmarks/%.set patch-cpp2py cpp2py.py
	@echo 'converting c benchmarks to python'
	@make -C benchmarks $*/ 

list-benchmarks:
	@echo benchmarks/*/ | sed  -e 's/ /\n/g' -e 's/benchmarks\///g' | sed -e '/^.*sv-/d'

regenerate-benchmark-%: benchmarks/%.set patch-cpp2py cpp2py.py
	@echo "converting c benchmark set $* to python"
	@rm -rf benchmarks/$*/
	@make -C benchmarks $*/ -B

# main target for generating benchmarks
generate-benchmarks: patch-cpp2py cpp2py.py 
	@echo "converting c benchmarks to python"
	@make -C benchmarks benchmarks -B

# main target for running benchmarks, TODO: define set of benchmark sets somewhere

run-benchmark-%: venv check-venv benchmarks/% cpp2py.py
	@echo 'running benchmark'
	python -m pycpa -p ReachSafety -c PredicateAnalysis --max-iterations 1 benchmarks/$*/*.py

run-benchmarks: run-benchmark-ReachSafety-Arrays/ run-benchmark-ControlFlow/ run-benchmark-Floats/ run-benchmark-Heap/ run-benchmark-Loops/ run-benchmark-ProductLines/ run-benchmark-Sequentialized/ run-benchmark-XCSP/ run-benchmark-Combinations/ 

run-benchmark-Test: 

run-examples: check-venv test_progs/*.py
	python -m pycpa -p ReachSafety -c PredicateAnalysis --max-iterations 300 test_progs/*.py benchmarks/Test/*.py


run-%: check-venv %.py
	python -m pycpa -p ReachSafety -c PredicateAnalysis --max-iterations 300 $*.py 



# separate file for testing
test: check-venv
	python -m pycpa.test
