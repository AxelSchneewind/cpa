

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
patch-cpp2py: cpp2py.py
	@echo 'patching cpp2py'
	@cp cpp2py.py ./venv/lib/python3.13/site-packages/cpp2py/cpp2py.py

benchmarks/%: benchmarks/%.set patch-cpp2py cpp2py.py
	@echo 'converting c benchmarks to python'
	@make -C benchmarks $*/

regenerate-benchmarks-%: benchmarks/%.set patch-cpp2py cpp2py.py
	@echo 'converting c benchmarks to python'
	@make -C benchmarks $*/ -B

run-benchmark-%: venv check-venv benchmarks/% cpp2py.py
	@echo 'running benchmark'
	python -m pycpa -p ReachSafety -c ValueAnalysisMergeJoin benchmarks/bitvector/*
