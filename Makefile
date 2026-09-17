.PHONY: docs ci lint mypy test-matrix ci-clean

docs:
	mkdocs serve -a 0.0.0.0:3250

# ---------------------------------------------------------------------------
# Local mirror of .github/workflows/ci.yml
#
#   make ci                                  lint + mypy + tests on every qm-qua version
#   make test-qm-qua-1.4.1                   tests against a single version
#   make ci QM_QUA_VERSIONS="1.4.0 1.4.1"    override the matrix
#   make ci-clean                            delete the CI virtualenvs
#
# Every job gets its own fresh virtualenv under .ci/, like a clean runner would.
# The matrix is read from ci.yml so the two can't drift apart.
# ---------------------------------------------------------------------------

PYTHON ?= python3
CI_DIR := .ci
QM_QUA_VERSIONS ?= $(shell grep -oP "qm-qua-version:\s*\[\K[^]]*" .github/workflows/ci.yml | tr -d "',")
TEST_JOBS := $(addprefix test-qm-qua-,$(QM_QUA_VERSIONS))

# Creates the venv (once) and installs the project with test extras into it.
# $(1) = venv dir
define setup_venv
	@test -x $(1)/bin/python || $(PYTHON) -m venv $(1)
	@$(1)/bin/pip install -q --upgrade pip
	@$(1)/bin/pip install -q -e ".[test]"
endef

# --keep-going mirrors `fail-fast: false`: every job runs, make exits non-zero if any failed.
ci:
	@$(MAKE) --no-print-directory --keep-going lint mypy test-matrix \
		&& echo "\n✅ CI passed" || (echo "\n❌ CI failed"; exit 1)

lint:
	@echo "==> lint"
	$(call setup_venv,$(CI_DIR)/base)
	$(CI_DIR)/base/bin/python -m ruff check .

mypy:
	@echo "==> mypy"
	$(call setup_venv,$(CI_DIR)/base)
	$(CI_DIR)/base/bin/python -m mypy qm_circuit

test-matrix: $(TEST_JOBS)

test-qm-qua-%:
	@echo "==> test (qm-qua==$*)"
	$(call setup_venv,$(CI_DIR)/qm-qua-$*)
	@$(CI_DIR)/qm-qua-$*/bin/pip install -q "qm-qua==$*"
	$(CI_DIR)/qm-qua-$*/bin/python -B -m pytest tests/

ci-clean:
	rm -rf $(CI_DIR)
