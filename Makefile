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

# check that source files for mathsat exist
check-msat-source: 
	@([ -n "$(MSAT-SRC-DIR)" ] && [ -d "$(MSAT-SRC-DIR)" ]) || (echo 'missing mathsat source files (please place the extracted mathsat archive into this directory)'; exit 1)

# checks if the required files for msat exist
check-msat-files: 
	@[ -e $(MSAT-PREFIX)/mathsat.py ] || (echo 'missing ' $(MSAT-PREFIX)/mathsat.py && exit 1)
	@[ -d $(MSAT-PREFIX)/mathsat/ ] || (echo 'missing ' $(MSAT-PREFIX)/mathsat/ && exit 1)
	@[ -e $(MSAT-PREFIX)/_mathsat.so ] || (echo 'missing ' $(MSAT-PREFIX)/_mathsat.so && exit 1)

PYTHONPATH::=$(MSAT-PREFIX)/:$(PYTHONPATH)
LD_LIBRARY_PATH::=$(MSAT-PREFIX)/mathsat/lib:$(LD_LIBRARY_PATH)

check-msat: venv check-msat-files
	PYTHONPATH=$(PYTHONPATH) LD_LIBRARY_PATH=$(LD_LIBRARY_PATH) pysmt-install --check

# no idea why this has to be so complicated
# copies the msat source directory into site-packages (not sure why this is required)
# copies the msat python file into site-packages
# copies the msat shared objects file into site-packages
install-msat: check-venv check-msat-source
	@echo 'installing mathsat' 
	cd ${MSAT-SRC-DIR}/python && python setup.py build && cd -
	rm -rf "${MSAT-PREFIX}"/msat "${MSAT-PREFIX}"/mathsat* "${MSAT-PREFIX}"/lib
	cp -r "${MSAT-SRC-DIR}/python/mathsat.py" "${MSAT-PREFIX}"/
	cp -r "${MSAT-SRC-DIR}/python/build"/lib.*/_mathsat*.so "${MSAT-PREFIX}"/_mathsat.so
	cp -r "${MSAT-SRC-DIR}/" "${MSAT-PREFIX}"/mathsat
	PYTHONPATH=$(PYTHONPATH) LD_LIBRARY_PATH=$(LD_LIBRARY_PATH) pysmt-install --check


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







########################### EXAMPLE TASK EXECUTION ############################

run-examples-%: check-msat-files
	@echo 'testing $* on example programs'
	@${PYTHON} -m pycpa -p unreach-call -c $* --compact --max-iterations 600 test_progs/*.yml test_progs/*.py -o out/$* 

run-examples: check-venv test_progs/*.py run-examples-PredicateAnalysisCEGAR run-examples-PredicateAnalysisABEf run-examples-PredicateAnalysisABEbf run-examples-ReachabilityAnalysis run-examples-ValueAnalysis run-examples-ValueAnalysisMergeJoin run-examples-FormulaAnalysis 

demo-example: check-venv
	@${PYTHON} -m pycpa -c ValueAnalysis --max-iterations 600 -o out-demo/ValueAnalysis test_progs/collatz_safe.py
	@${PYTHON} -m pycpa -c PredicateAnalysis --max-iterations 600 -o out-demo/PredicateAnalysis test_progs/collatz_safe.py
	@${PYTHON} -m pycpa -c PredicateAnalysisABEbf --max-iterations 600 -o out-demo/PredicateAnalysisABEbf test_progs/collatz_safe.py
	@${PYTHON} -m pycpa -c PredicateAnalysisCEGAR --max-iterations 600 -o out-demo/PredicateAnalysisCEGAR test_progs/collatz_safe.py



############################### BENCHEXEC ######################################

# Root path of the artifact
BASE-PATH = $(shell dirname $(abspath $(lastword $(MAKEFILE_LIST))))

# Output path of the tool(s)
output-path = ./results
ABS-OUTPUT-PATH = $(abspath ${output-path})

# CPAchecker variables
CPA-PATH = ${BASE-PATH}/pycpa/
CPA-EXE = ${CPA-PATH}/scripts/cpa.sh
CPA-DEFAULT-ARGS =

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
BENCHEXEC-CALL=PYTHONPATH=$(PYTHONPATH) LD_LIBRARY_PATH=$(LD_LIBRARY_PATH) ${benchexec-call-prefix} ${benchexec} ${benchexec-args} ${BENCHEXEC-RESOURCES} ${BENCHEXEC-DIRS}
BENCHDEFS-PATH = bench-defs
ABS-BENCHDEFS-PATH = "${BASE-PATH}/bench-defs"

# Table-Generator variables
table-generator = table-generator
TABLE-GENERATOR-ARGS = -f html --no-diff -c -o ${ABS-OUTPUT-PATH}/
TABLE-GENERATOR-CALL = ${table-generator} ${TABLE-GENERATOR-ARGS}

PYTHON = PYTHONPATH=$(PYTHONPATH) LD_LIBRARY_PATH=$(LD_LIBRARY_PATH) python
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
	${benchexec-call-prefix} ${PYTHON} -m benchexec.test_tool_info cpachecker ${BENCHEXECBASE-DIRS}


# Run experiments
run-demo-exp: check-output-exist ${TOOLDEF-FILE} check-msat-files check-venv
	${BENCHEXEC-CALL} "${BENCHDEFS-PATH}/pycpa-demo.xml"

run-medium-exp: check-output-exist ${TOOLDEF-FILE} check-msat-files check-venv
	${BENCHEXEC-CALL} "${BENCHDEFS-PATH}/pycpa-medium.xml"

# Generate tables from the experiments
gen-%-table:
	${TABLE-GENERATOR-CALL} -x ${ABS-BENCHDEFS-PATH}/stats.$*.xml -o ${ABS-OUTPUT-PATH}






############################### DEBUGGING ######################################

# separate file for testing
test: check-venv
	python -m pycpa.test

run-bad: 
	${PYTHON} -m pycpa --compact -p unreach-call -o out-bad -c PredicateAnalysisABElf --max-iterations 300 test_progs/*.yml

