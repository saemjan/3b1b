# The core is plain C++17 with no libraries. These targets only call
# tools/build.py, which holds the real recipe. The Makefile routes; it
# never cooks (rule R21).
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
ref-test:
	node --test reference/test/*.test.js
diff: cli
	python3 tests/diff/run.py
test: ref-test diff lib
	python3 -m pytest -q
clean:
	rm -rf build
