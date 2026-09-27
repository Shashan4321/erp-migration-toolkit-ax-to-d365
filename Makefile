.PHONY: all generate profile migrate reconcile bc-export ax-views test lint

all: generate profile reconcile bc-export ax-views

generate:        ## 1. synthetic AX extracts -> data/source_ax/
	PYTHONPATH=src python -m erpmig.generate_ax

profile:         ## 2. data profiling -> reports/profiling.md
	PYTHONPATH=src python -m erpmig.profile

migrate:         ## 3. transform to BC-ready files -> data/target_bc/, data/rejects/
	PYTHONPATH=src python -m erpmig.migrate

reconcile:       ## 4. migrate + reconcile -> reports/reconciliation.md (exit 1 on failure)
	PYTHONPATH=src python -m erpmig.reconcile

bc-export:       ## 5. after go-live: BC export in the bc2adls layout -> data/bc_export/deltas/
	PYTHONPATH=src python -m erpmig.bc_export

ax-views:        ## 6. AX-compatible T-SQL views on the export -> reports/ax_views_reconciliation.md (exit 1 on failure)
	PYTHONPATH=src python -m erpmig.ax_views

test:
	pytest -q

lint:
	ruff check . && ruff format --check .
