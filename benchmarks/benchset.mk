# Makefile for generating python test-programs from sv-comp files.
#
# This is a very non-elegant solution. 
# For a possible output file, we don't know which task it belongs 
# to (and where to find it). For this reason, we cannot simply 
# specify a target pattern for the resulting python file.
# Instead, we have target patterns that get the original task 
# and generate the respective files from that.

# output formatting
FORMAT_STATUS=column -s ':' -C name=program,width=60,left -C name=status,right,width=20 --table -d


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


# checks that the referenced program file for a task exists and gets the files
.phony: %.yml.get
%.yml.get: %.yml
	@cprog=$(*D)/$$(grep "input_files: .*" "$*.yml" | sed "s/input_files: //" | sed "s/'//g") \
	 && [ -s $$cprog ] && (cp -f $*.yml . ; cp -f $$cprog $(*F).c)

# checks if a c program can be transpiled (i.e. does not contain blacklisted keywords)
.phony: %.c.check
%.c.check:
	@$(shell grep -F -f ../blacklist-keywords.txt $(*F).c > error_$(*F))

# adjusts the program name for a task (given by relative path)
# ensures that task and program files have the same base name
.phony: %.yml.setprogram
%.yml.setprogram: %.c
	@sed 's/input_files\s*:.*/input_files: $(*F).py/' -i $(*F).yml

# cleans up empty files after transpilation
# ensures that if error_NAME exists and is non-empty, then NAME.yml does not exist
# ensures that if NAME.py does not exist or is non-empty, then NAME.yml does not exist
.phony: %.yml.cleanup
%.yml.cleanup:
	@[ ! -e error_$(*F) ]      || ([ -s error_$(*F) ] || rm -f error_$(*F))
	@[ ! -e error_$(*F) ]      || rm -f $(*F).yml
	@[ ! -e $(*F).py ]         || ([ -s $(*F).py ] || rm -f $(*F).py)
	@[ -e $(*F).py ]           || rm -f $(*F).yml
	@[ ! -e $(*F).c.prepared ] || rm -f $(*F).c.prepared

# prepares a c file for transpilation
%.c.prepared: %.c
	@gcc -E $(*F).c -o $(*F).i
	@sed -f ../prepare_c.txt "$(*F).i" > $(*F).c.prepared
	@rm $(*F).i

# transpiles a c file to python
%.py: %.c.prepared
	@../transpile.sh "$(*F).c.prepared" "$(*F).py" ../ignore-symbols.txt 2> error_$(*F) 

# prints status after transpilation
.phony: %.yml.status
%.yml.status:
	@([ -s $(*F).yml ] && echo '$(*F):success' || echo '$(*F):failure') | $(FORMAT_STATUS)

# command for recursively invoking make
MAKE_REC=$(MAKE) --file=../benchset.mk

# this recipe does the heavy lifting:
# it gets the task file and reads the c-file from it,
# copies it here and transpiles to python.
# The resulting file is checked, invalid files get removed.
.phony: %.yml.setup 
%.yml.setup: %.yml.get
	@[   -s "$*.yml"   ] || (echo '$(*F):task missing/invalid' | $(FORMAT_STATUS); exit 0)
	@[ ! -s "$(*F).py" ] || (echo '$(*F):already exists' | $(FORMAT_STATUS); exit 0)
	@$(MAKE_REC) $*.c $*.yml.setprogram $*.c.check
	@[ -s "$(*F).c" ] || (echo "   $(*F).c missing or invalid"; exit 0)
	@$(MAKE_REC) $*.py
	@$(MAKE_REC) $(*F).yml.cleanup $(*F).yml.status



