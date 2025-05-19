for prog in test_progs/*.py; do
  echo "=== Running $prog ==="
  python -m pycpa "$prog" -c PredicateAnalysis -p ReachSafety --max-iterations 1000
done

