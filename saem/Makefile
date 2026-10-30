# The core is plain C++17 with no libraries. These targets only call tools/build.py, which holds the real recipe.
.PHONY: all cli lib test ref-test diff clean id c17
all: cli lib
cli:
	python3 tools/build.py cli
lib:
	python3 tools/build.py lib
id:
	python3 tools/build.py id
ref-test:            # the JavaScript reference engine's own tests (development only)
	node --test "reference/test/*.test.js"
diff: cli            # C++ core against the JavaScript reference, case by case
	python3 tests/diff/run.py
test: ref-test diff
	python3 -m unittest discover -s tests -p "test_*.py"
c17:                 # the C17 sovereign kernel: strict builds, zero-heap proof, all tests under sanitizers, cross-checks
	python3 tools/check_c17.py
clean:
	rm -rf build build_c17
