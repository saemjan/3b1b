# The core is plain C++17 with no libraries. These targets only call
# tools/build.py, which holds the real recipe. The Makefile is a clerk,
# not a kitchen: it routes, it never cooks.
.PHONY: all cli lib id verify test ref-test diff clean
all: cli lib
cli:
	python3 tools/build.py cli
lib:
	python3 tools/build.py lib
id:
	python3 tools/build.py id
verify: cli
	python3 tools/build.py verify
ref-test: # the JavaScript reference engine's own tests (development only)
	node --test reference/test/*.test.js
diff: cli # C++ core against the JavaScript reference, case by case
	python3 tests/diff/run.py
test: ref-test diff lib # three witnesses; lib so no witness is blind
	python3 -m unittest discover -s tests -p "test_*.py"
clean:
	rm -rf build
