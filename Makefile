

# TODO add hint about activation
check-venv:
	@[ -d venv ] || make help-venv

help-venv:
	@echo 'setup the virtual environment first by running:'
	@echo 'python -m venv venv'
	@echo './venv/bin/pip install cpp2py'
	@exit

# the cpp2py required for benchmark generation seems to be abandoned and has bugs
# use this target to use a (partially) fixed version supplied here
# Note: this still does not support e.g. goto
patch-cpp2py:
	@cp cpp2py.py ./venv/lib/python3.13/site-packages/cpp2py/cpp2py.py

generate-benchmarks: path-cpp2py


run: check-venv 

