# Makefile for generating python test-programs from sv-comp files.
#
# This is a very non-elegant solution. 
# For a possible output file, we don't know which task it belongs 
# to (and where to find it). For this reason, we cannot simply 
# specify a target pattern for the resulting python file.
# Instead, we have target patterns that get the original task 
# and generate the respective files from that.


# copy the file (from the target stem) to this directory
.phony: %.get
%.get:
	@cp -f $* . || echo '$* does not exist'

# checks if a python file is valid syntactically and deletes it if not
.phony: %.py.check
%.py.check:
	@([ -e $*.py ] && (python -m py_compile $*.py >> error_$* 2>&1)) || exit 1

.phony: %.c.check
%.c.check:
	@[ -z "$$(grep -f ../blacklist-keywords.txt $(*F).c)" ] || exit 1

# gets a program file for a task (requires full path)
.phony: %.yml.getprogram
%.yml.getprogram:
	@cprog=$(*D)/$$(grep "input_files: .*" "$(*F).yml" | sed "s/input_files: //" | sed "s/'//g") \
	 && [ ! -e $$cprog ] || cp -f $$cprog "$(*F).c"

# checks that the referenced program file exists
.phony: %.yml.check
%.yml.check:
	@cprog=$(*D)/$$(grep "input_files: .*" "$(*F).yml" | sed "s/input_files: //" | sed "s/'//g") \
	 && [ -e $$cprog ] || rm $*.yml

# adjusts the program name for a task (given by relative path)
# ensures that task and program files have the same base name
.phony: %.yml.getprogram
%.yml.setprogram:
	@sed 's/input_files\s*:.*/input_files: $(*F).py/' -i $(*F).yml

# prepares a c file for transpilation
%.c.prepare: 
	@sed -f ../prepare_c.txt -i "$(*F).c"

# transpiles a c file to python
%.c.transpile: 
	@../transpile.sh "$(*F).c"

# this recipe does the heavy lifting:
# it gets the task file and reads the c-file from it,
# copies it here and transpiles to python.
# The resulting file is checked, invalid files get removed.
.phony: %.yml.setup
%.yml.setup:
	@make -s $*.yml.get > /dev/null
	@[ -e "$*.yml" ]     || (echo '$(*F): task missing' && exit 0)
	@[ ! -e "$(*F).py" ] || (echo '$(*F): already exists' && exit 0)
	@echo '$*: transpiling...'
	@make -s $*.yml.getprogram || exit 0
	@make -s $*.yml.setprogram || exit 0
	@[ -e "$(*F).c" ] || (echo "$(*F).c missing" && exit 0)
	@make -s $*.c.check || exit 0
	@make -s $*.c.prepare
	@make -s $*.c.transpile
	@make -s $*.yml.check $(*F).py.check || rm $(*F).*

# main target, consisting of tasks from Task set
TASKSET=$(wildcard *.set)
TASKS=$(wildcard $(shell cat $(TASKSET)))
RECIPES=$(subst .yml,.yml.setup,$(TASKS))
all: $(RECIPES)
