
%/: %.set properties/
	./transpile_set.sh $*

properties/: sv-benchmarks/c/properties
	ln -s sv-benchmarks/c/properties properties

sets: ReachSafety-Arrays.set ReachSafety-ControlFlow.set ReachSafety-ECA.set ReachSafety-Floats.set ReachSafety-Heap.set ReachSafety-Loops.set ReachSafety-ProductLines.set ReachSafety-Sequentialized.set ReachSafety-XCSP.set ReachSafety-Combinations.set ReachSafety-Hardware.set SoftwareSystems-AWS-C-Common-ReachSafety.set SoftwareSystems-DeviceDriversLinux64-ReachSafety.set SoftwareSystems-uthash-ReachSafety.set

# not elegant but works for me
%.set: sv-benchmarks/c/%.set
	@(cat sv-benchmarks/c/$*.set | sed -e '/^\s*#.*/d' | sed -e 's/\.yml/.c/' | sed -e 's/^/echo sv-benchmarks\/c\//g') > $*.tmp
	@(bash $*.tmp | sed -e 's/ /\n/g') > $*.set
	@rm $*.tmp


.phony: benchmarks
benchmarks: ReachSafety-Arrays/ ReachSafety-ControlFlow/ ReachSafety-ECA/ ReachSafety-Floats/ ReachSafety-Heap/ ReachSafety-Loops/ ReachSafety-ProductLines/ ReachSafety-Sequentialized/ ReachSafety-XCSP/ ReachSafety-Combinations/ ReachSafety-Hardware/ SoftwareSystems-AWS-C-Common-ReachSafety/ SoftwareSystems-DeviceDriversLinux64-ReachSafety/ SoftwareSystems-uthash-ReachSafety/


