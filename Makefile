.PHONY: all generate profile migrate reconcile test lint

all: generate profile reconcile

generate:        ## 1. synthetic AX extracts -> data/source_ax/
	PYTHONPATH=src python -m erpmig.generate_ax

profile:         ## 2. data profiling -> reports/profiling.md
	PYTHONPATH=src python -m erpmig.profile

migrate:         ## 3. transform to BC-ready files -> data/target_bc/, data/rejects/
	PYTHONPATH=src python -m erpmig.migrate

reconcile:       ## 4. migrate + reconcile -> reports/reconciliation.md (exit 1 on failure)
	PYTHONPATH=src python -m erpmig.reconcile

test:
	pytest -q

lint:
	ruff check . && ruff format --check .
