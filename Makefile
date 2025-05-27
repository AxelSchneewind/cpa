########################### VIRTUAL ENVIRONMENT ###############################

# venv is required for benchmark generation
venv:
	@echo 'setting up the virtual environment'
	python -m venv venv
	./venv/bin/pip install -r requirements.txt
	@echo 'installint math-sat solver'
	@make install-msat
	@echo 'use '
	@echo '  source venv/bin/activate'
	@echo 'to activate'

check-venv:
	@[ ! -z "$(VIRTUAL_ENV)" ] || (echo 'activate the virtual environment first using source venv/bin/activate' && exit 1)

# exports for msat
export PYTHONPATH+=:${BASE-PATH}/venv/lib/python3.13/site-packages/mathsat/python/build/
export LD_LIBRARY_PATH+=:${BASE-PATH}/venv/lib/python3.13/site-packages/mathsat/lib

check-msat: venv
	pysmt-install --check

install-msat:
	@echo 'installing mathsat' 
	@cd mathsat-*/python/ && python -m pip install . && cd -
	@cp mathsat-*/python/mathsat.py venv/lib/python3.13/site-packages/
	@cp mathsat-*/python/build/lib.*/_mathsat.* venv/lib/python3.13/site-packages/mathsat.so


# the cpp2py required for benchmark generation seems to be abandoned and has bugs
# use this target to use a (partially) fixed version supplied here
# Note: this still does not support e.g. goto
.phony: path-cpp2py
patch-cpp2py: cpp2py.py
	@echo 'patching cpp2py'
	@cp cpp2py.py ./venv/lib/python3.13/site-packages/cpp2py/cpp2py.py





############################ BENCHMARK GENERATION ##############################

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







############################ BENCHMARK EXECUTION ###############################

# main target for running benchmarks
run-benchmark-%: venv check-venv benchmarks/% cpp2py.py
	@echo 'running benchmark'
	python -m pycpa -p ReachSafety -c PredicateAnalysis --max-iterations 1 benchmarks/$*/*.py

run-examples-%:
	@echo 'testing $* on example programs'
	@python -m pycpa -p ReachSafety -c $* --compact --max-iterations 600 test_progs/*.py -o out/$* 

run-examples: check-venv test_progs/*.py run-examples-PredicateAnalysisCEGAR run-examples-PredicateAnalysis run-examples-PredicateAnalysisABEf run-examples-PredicateAnalysisABEbf run-examples-ReachabilityAnalysis run-examples-ValueAnalysis run-examples-ValueAnalysisMergeJoin run-examples-FormulaAnalysis 

run-%: check-venv %.py
	python -m pycpa -p ReachSafety -c PredicateAnalysis --max-iterations 300 $*.py 



############################### BENCHEXEC ######################################

# Root path of the artifact
BASE-PATH = $(shell dirname $(abspath $(lastword $(MAKEFILE_LIST))))

# Output path of the tool(s)
output-path = ./results
ABS-OUTPUT-PATH = $(abspath ${output-path})

# CPAchecker variables
# c-prog = ${BASE-PATH}/sv-benchmarks/c/loop-invariants/const.c
CPA-PATH = ${BASE-PATH}/pycpa/
CPA-EXE = ${CPA-PATH}/scripts/cpa.sh
CPA-DEFAULT-ARGS = --spec sv-comp-reachability \
	--option cpa.predicate.memoryAllocationsAlwaysSucceed=true
cpa-args = --32

# BenchExec variables
benchexec-call-prefix=
benchexec=benchexec

timelimit = 300s
memlimit = 2500MB
cpulimit = 2
benchexec-args =
BENCHEXEC-RESOURCES = -T ${timelimit} -M ${memlimit} -c ${cpulimit}
BENCHEXECBASE-DIRS = --read-only-dir / --hidden-dir /home/ --overlay-dir "${BASE-PATH}/"
BENCHEXEC-DIRS = ${BENCHEXECBASE-DIRS} --tool-directory "${CPA-PATH}/" -o "${ABS-OUTPUT-PATH}"/
BENCHEXEC-CALL = ${benchexec-call-prefix} ${benchexec} ${benchexec-args} ${BENCHEXEC-RESOURCES} ${BENCHEXEC-DIRS}
BENCHDEFS-PATH = bench-defs
ABS-BENCHDEFS-PATH = "${BASE-PATH}/bench-defs"

# Table-Generator variables
table-generator = table-generator
TABLE-GENERATOR-ARGS = -f html --no-diff -c -o ${ABS-OUTPUT-PATH}/
TABLE-GENERATOR-CALL = ${table-generator} ${TABLE-GENERATOR-ARGS}

PYTHON = python3
export PATH+=:${BASE-PATH}/benchexec/bin/:${BASE-PATH}/pycpa/
export PYTHONPATH+=:${BASE-PATH}/benchexec/

default:
	@echo "Please specify a make target!"

# @sudo swapoff -a
prepare-benchexec:
	@sudo sysctl -w kernel.unprivileged_userns_clone=1
	@sudo sysctl -w user.max_user_namespaces=10000

test-cgroups:
	@${benchexec-call-prefix} ${PYTHON} -m benchexec.check_cgroups && echo "Check passed"

# Run experiments
run-demo-exp: check-output-exist
	${BENCHEXEC-CALL} "${BENCHDEFS-PATH}/cpachecker-demo.xml"

run-full-exp: check-output-exist
	${BENCHEXEC-CALL} "${BENCHDEFS-PATH}/cpachecker.xml"

# Generate tables from the experiments
gen-full-table:
	${TABLE-GENERATOR-CALL} -x ${ABS-BENCHDEFS-PATH}/stats.overall.xml -o ${ABS-OUTPUT-PATH}

gen-demo-table:
	${TABLE-GENERATOR-CALL} -x ${ABS-BENCHDEFS-PATH}/stats.demo.xml -o ${ABS-OUTPUT-PATH}


# Cleaning up files
check-output-exist:
	@if [ -d ${ABS-OUTPUT-PATH} ]; then \
		echo "Output folder '${ABS-OUTPUT-PATH}' already exists."; \
		echo "Please rename the folder or run 'make clean-results' first."; \
		exit 1; \
	fi

clean-results:
	@rm -rf ${ABS-OUTPUT-PATH}

# Root path of the artifact
BASE-PATH = $(shell dirname $(abspath $(lastword $(MAKEFILE_LIST))))

# Output path of the tool(s)
output-path = ./results
ABS-OUTPUT-PATH = $(abspath ${output-path})

# test tool definition
benchexec-test-tooldef:
	${benchexec-call-prefix} ${PYTHON} -m benchexec.test_tool_info pycpa ${BENCHEXECBASE-DIRS}







############################### DEBUGGING ######################################

# separate file for testing
test: check-venv
	python -m pycpa.test

run-bad: 
	python -m pycpa -p ReachSafety -c PredicateAnalysis --max-iterations 300 test_progs/collatz_safe.py benchmarks/Test/btor2c-lazyMod.anderson.6.prop1-back-serstep.c.py
