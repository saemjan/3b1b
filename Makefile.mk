PYTHON ?= python3

.PHONY: all cli lib id verify clean test

all: ; $(PYTHON) tools/build.py all
cli: ; $(PYTHON) tools/build.py cli
lib: ; $(PYTHON) tools/build.py lib
id: ; $(PYTHON) tools/build.py id
verify: ; $(PYTHON) tools/build.py verify
clean: ; $(PYTHON) tools/build.py clean

test: cli
	$(PYTHON) tools/build.py verify
	./build/saem_cli --source-id
	echo '{"id":1,"method":"gen.topics","args":{}}' | ./build/saem_cli
	echo '{"id":2,"method":"qcos.boot","args":{}}' | ./build/saem_cli
