# Makefile for generating python test-programs from sv-comp files.
#
# This is a very non-elegant solution. 
# For a possible output file, we don't know which task it belongs 
# to (and where to find it). For this reason, we cannot simply 
# specify a target pattern for the resulting python file.
# Instead, we have target patterns that get the original task 
# and generate the respective files from that.

# has to be set when invoking main target of this makefile
# SV-BENCH-DIR=
.phony: check-sv-bench-dir
check-sv-bench-dir:
	@[ -n "$(SV-BENCH-DIR)" ] || (echo 'SV-BENCH-DIR has to be set'; exit 0)

# main target, consisting of tasks from Task set
TASKSET=$(wildcard *.set)
TASKS=$(wildcard $(patsubst %,$(SV-BENCH-DIR)/%,$(shell cat $(TASKSET))))
RECIPES=$(patsubst %.yml,%.yml.setup,$(TASKS))

.phony: all
all: check-sv-bench-dir $(RECIPES)

.phony: clean
clean:
	rm -f *.py *.c *.yml *.cil error_*


# copy the file (from the target stem) to this directory
.phony: %.yml.get
%.yml.get:
	@cp -f $*.yml . || echo '$* does not exist'
.phony: %.c.get
%.c.get:
	@cp -f $*.c .   || echo '$* does not exist'

# checks if a c program can be transpiled (i.e. does not contain blacklisted keywords)
.phony: %.c.check
%.c.check:
	@[ -z "$$(grep -f ../blacklist-keywords.txt $(*F).c)" ] || exit 0


# checks if a python file is valid syntactically
# if invalid: reason in error_[filename]
.phony: %.py.check
%.py.check:
	@([ ! -s $(*F).py ] || (python -m py_compile $(*F).py 2> error_$(*F)))
	@([ ! -e error_$(*F) ] || ([ -s $(*F).py ] || rm -f error_$(*F)))


# checks that the referenced program file exists
.phony: %.yml.check
%.yml.check:
	@cprog=$(*D)/$$(grep "input_files: .*" "$(*F).yml" | sed "s/input_files: //" | sed "s/'//g") \
	 && ([ -s $$cprog ] || (rm $(*F).yml ; exit 0))

# gets a program file for a task (requires stem to be full path)
.phony: %.yml.getprogram
%.yml.getprogram:
	@cprog=$(*D)/$$(grep "input_files: .*" "$(*F).yml" | sed "s/input_files: //" | sed "s/'//g") \
	 && ([ ! -e $$cprog ] || cp -f $$cprog "$(*F).c")

# adjusts the program name for a task (given by relative path)
# ensures that task and program files have the same base name
.phony: %.yml.setprogram
%.yml.setprogram:
	@sed 's/input_files\s*:.*/input_files: $(*F).py/' -i $(*F).yml

# prepares a c file for transpilation
.phony: %.c.prepare
%.c.prepare: 
	@sed -f ../prepare_c.txt -i "$(*F).c"

# transpiles a c file to python
.phony: %.c.transpile
%.c.transpile: 
	@../transpile.sh "$(*F).c" ../ignore-symbols.txt

# command for recursively invoking make
MAKE_REC=$(MAKE) --file=../benchset.mk

# this recipe does the heavy lifting:
# it gets the task file and reads the c-file from it,
# copies it here and transpiles to python.
# The resulting file is checked, invalid files get removed.
.phony: %.yml.setup 
%.yml.setup:
	@$(MAKE_REC) $*.yml.get
	@[ -s "$*.yml" ]     || (echo '$(*F): task missing'; exit 0)
	@[ ! -s "$(*F).py" ] || (echo '$(*F): already exists'; exit 0)
	@$(MAKE_REC) $*.yml.check || exit 0
	@$(MAKE_REC) $*.yml.getprogram || exit 0
	@$(MAKE_REC) $*.yml.setprogram || exit 0
	@[ -s "$(*F).c" ] || (echo "   $(*F).c missing"; exit 0)
	@$(MAKE_REC) $*.c.check || exit 0
	@$(MAKE_REC) $*.c.prepare || exit 0
	@$(MAKE_REC) $*.c.transpile
	@$(MAKE_REC) $(*F).py.check || (rm -f $(*F).*; exit 0)
	@echo "$(*F): success"



