
sv-benchmarks/c/properties/:
	@[ -d $@ ] || (echo '$@ does not exist, maybe you forgot to checkout the submodule?' && exit 1)

properties/: sv-benchmarks/c/properties/
	@[ -d $@ ] || cp -r sv-benchmarks/c/properties .

# print information about the generated benchmark set
.phony: ReachSafety-%.stats
ReachSafety-%.stats: 
	@echo "ReachSafety-$*: "
	@echo "   transpiled programs: $(shell echo ReachSafety-$*/*.py | wc -w)"
	@echo "   invalid    programs: $(shell echo ReachSafety-$*/error_* | wc -w)"

# print information about the generated benchmark set
.phony: ReachSafety-%.list
ReachSafety-%.list: 
	@echo "ReachSafety-$*: "
	@$(foreach name, $(patsubst ReachSafety-$*/%.yml,%,  $(wildcard ReachSafety-$*/*.yml)  ), echo -e "$(name): \tsuccess" ;)
	@$(foreach name, $(patsubst ReachSafety-$*/error_%,%,$(wildcard ReachSafety-$*/error_*)), echo -e "$(name): \tfailure" ;)

# clean a benchmark set
.phony: ReachSafety-%.clean
ReachSafety-%.clean: 
	@echo "cleaning ReachSafety-$*"
	@make -s -r --file=../benchset.mk -C ReachSafety-$* clean

.phony: ReachSafety-%.generate
ReachSafety-%.generate: properties/ ReachSafety-%/*.set
	@echo "generating ReachSafety-$*"
	@make -s -r --file=../benchset.mk -C ReachSafety-$*/ SV-BENCH-DIR=../sv-benchmarks/c all
	@make ReachSafety-$*.stats

.phony: all
REACHSAFETY=$(wildcard ReachSafety-*/)
all: $(patsubst %/,%.generate,$(REACHSAFETY))

.phony: clean
clean: $(patsubst %/,%.clean,$(REACHSAFETY))

.phony: stats
stats: $(patsubst %/,%.stats,$(REACHSAFETY))

.phony: list
list: $(patsubst %/,%.list,$(REACHSAFETY))