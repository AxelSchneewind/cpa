########################### VIRTUAL ENVIRONMENT ###############################

# venv is required for benchmark generation
venv: 
	@echo 'setting up the virtual environment'
	python -m venv venv
	./venv/bin/pip install -r requirements.txt
	@echo 'installing math-sat solver'
	@make install-msat

check-venv:
	@[ ! -z "$(VIRTUAL_ENV)" ] || (echo -e 'use \n  source venv/bin/activate\nto activate' && exit 1)


##################################### MSAT ####################################
MSAT-SRC-DIR=$(wildcard mathsat-*/)
MSAT-PREFIX=$(shell pwd)/venv/lib/python3.13/site-packages

# checks if the defined paths for msat are correct
check-msat-path: 
	@[ -e $(MSAT-PREFIX)/mathsat/python/ ] || (echo 'missing ' $(MSAT-PREFIX)/mathsat/python && exit 1)
	@[ -e $(MSAT-PREFIX)/mathsat/lib/ ] || (echo 'missing ' $(MSAT-PREFIX)/mathsat/lib && exit 1)

check-msat: venv check-msat-path
	pysmt-install --check


# 
PYTHONPATH::=$(MSAT-PREFIX)/mathsat/python/:$(PYTHONPATH)
LD_LIBRARY_PATH::=$(MSAT-PREFIX)/mathsat/lib:$(LD_LIBRARY_PATH)

install-msat: check-venv
	@echo 'installing mathsat' 
	cd ${MSAT-SRC-DIR}/python && python setup.py build && cd -
	rm -rf "${MSAT-PREFIX}"/msat "${MSAT-PREFIX}"/mathsat* "${MSAT-PREFIX}"/lib
	cp -r "${MSAT-SRC-DIR}" "${MSAT-PREFIX}"/mathsat
	PYTHONPATH=$(PYTHONPATH) LD_LIBRARY_PATH=$(LD_LIBRARY_PATH) pysmt-install --check


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

run-examples-%: check-msat-path
	@echo 'testing $* on example programs'
	@PYTHONPATH=$(PYTHONPATH) LD_LIBRARY_PATH=$(LD_LIBRARY_PATH) python -m pycpa -p ReachSafety -c $* --compact --max-iterations 600 test_progs/*.yml test_progs/*.py -o out/$* 

run-examples: check-venv test_progs/*.py run-examples-PredicateAnalysisCEGAR run-examples-PredicateAnalysisABEf run-examples-PredicateAnalysisABEbf run-examples-ReachabilityAnalysis run-examples-ValueAnalysis run-examples-ValueAnalysisMergeJoin run-examples-FormulaAnalysis 

run-%: check-venv %.py check-msat-path
	PYTHONPATH=$(PYTHONPATH) LD_LIBRARY_PATH=$(LD_LIBRARY_PATH) python -m pycpa -p ReachSafety -c PredicateAnalysis --max-iterations 300 $*.py 



############################### BENCHEXEC ######################################

# Root path of the artifact
BASE-PATH = $(shell dirname $(abspath $(lastword $(MAKEFILE_LIST))))

# Output path of the tool(s)
output-path = ./results
ABS-OUTPUT-PATH = $(abspath ${output-path})

# CPAchecker variables
CPA-PATH = ${BASE-PATH}/pycpa/
CPA-EXE = ${CPA-PATH}/scripts/cpa.sh
CPA-DEFAULT-ARGS = --property ReachSafety

# BenchExec variables
benchexec-call-prefix=
benchexec=benchexec

timelimit = 300s
memlimit = 1500MB
cpulimit = 2
benchexec-args = --numOfThreads=4
BENCHEXEC-RESOURCES = -T ${timelimit} -M ${memlimit} -c ${cpulimit}
BENCHEXECBASE-DIRS = --read-only-dir / --hidden-dir /home/ --overlay-dir "${BASE-PATH}/" --tool-directory "${CPA-PATH}/" 
BENCHEXEC-DIRS = ${BENCHEXECBASE-DIRS} -o "${ABS-OUTPUT-PATH}"/
BENCHEXEC-CALL = PYTHONPATH=$(PYTHONPATH) LD_LIBRARY_PATH=$(LD_LIBRARY_PATH) ${benchexec-call-prefix} ${benchexec} ${benchexec-args} ${BENCHEXEC-RESOURCES} ${BENCHEXEC-DIRS}
BENCHDEFS-PATH = bench-defs
ABS-BENCHDEFS-PATH = "${BASE-PATH}/bench-defs"

# Table-Generator variables
table-generator = table-generator
TABLE-GENERATOR-ARGS = -f html --no-diff -c -o ${ABS-OUTPUT-PATH}/
TABLE-GENERATOR-CALL = ${table-generator} ${TABLE-GENERATOR-ARGS}

PYTHON = python3
export PATH::=${BASE-PATH}/benchexec/bin/:${BASE-PATH}/pycpa/:$(PATH)
export PYTHONPATH::=${BASE-PATH}/benchexec/:$(PYTHONPATH)

default:
	@echo "Please specify a make target!"

# @sudo swapoff -a
prepare-benchexec:
	@sudo sysctl -w kernel.unprivileged_userns_clone=1
	@sudo sysctl -w user.max_user_namespaces=10000

test-cgroups:
	@${benchexec-call-prefix} ${PYTHON} -m benchexec.check_cgroups && echo "Check passed"


# Cleaning up files
check-output-exist:
	@if [ -d ${ABS-OUTPUT-PATH} ]; then \
		echo "Output folder '${ABS-OUTPUT-PATH}' already exists."; \
		echo "Please rename the folder or run 'make clean-results' first."; \
		exit 1; \
	fi

clean-results:
	@rm -rf ${ABS-OUTPUT-PATH}

TOOLDEF-FILE=benchexec/benchexec/tools/pycpa.py
${TOOLDEF-FILE}:
	cp pycpa-tooldef.py ${TOOLDEF-FILE}

# test tool definition
benchexec-test-tooldef: ${TOOLDEF-FILE}
	${benchexec-call-prefix} ${PYTHON} -m benchexec.test_tool_info pycpa ${BENCHEXECBASE-DIRS}


# Run experiments
run-demo-exp: check-output-exist ${TOOLDEF-FILE} check-msat-path check-venv
	${BENCHEXEC-CALL} "${BENCHDEFS-PATH}/pycpa-demo.xml"

run-medium-exp: check-output-exist ${TOOLDEF-FILE} check-msat-path check-venv
	${BENCHEXEC-CALL} "${BENCHDEFS-PATH}/pycpa-medium.xml"

# Generate tables from the experiments
gen-%-table:
	${TABLE-GENERATOR-CALL} -x ${ABS-BENCHDEFS-PATH}/stats.$*.xml -o ${ABS-OUTPUT-PATH}






############################### DEBUGGING ######################################

# separate file for testing
test: check-venv
	python -m pycpa.test

run-bad: 
	python -m pycpa -p ReachSafety -c PredicateAnalysis --max-iterations 300 test_progs/collatz_safe.py benchmarks/Test/btor2c-lazyMod.anderson.6.prop1-back-serstep.c.py
