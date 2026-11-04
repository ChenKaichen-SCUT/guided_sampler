.DEFAULT_GOAL := help
JOBS ?= 4
PYTHON ?= python3

.PHONY: help build test smoke-test
help:
	@echo "make build JOBS=4  Build the bundled Z3 and HighDiv locally"
	@echo "make test          Run build, initialization, runner, and metric checks"
	@echo "make smoke-test    Generate and validate a small set of samples"
	@echo "See README.md for installation and usage instructions."

build:
	bash scripts/build.sh --jobs $(JOBS)

test:
	$(PYTHON) -m unittest discover -s tests -v

smoke-test:
	bash scripts/smoke-test.sh
