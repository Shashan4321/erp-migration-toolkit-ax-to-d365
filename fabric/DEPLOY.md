# Deploy the AX-compatible reporting layer on Microsoft Fabric

About 20 minutes on a **free Fabric trial**. Use your own trial workspace, never a company tenant: everything here is synthetic.

## 1. Prepare the data locally

```bash
pip install -r requirements-dev.txt
make bc-export      # -> data/bc_export/deltas/<Table>-<Id>/   (Delta, bc2adls layout)
make ax-views       # runs the same views locally and writes reports/ax_views_reconciliation.md
```

## 2. Create the lakehouse

1. [app.fabric.microsoft.com](https://app.fabric.microsoft.com) → start the trial if asked → **Workspaces → New workspace** (e.g. `portfolio-bc-reporting`, trial capacity).
2. **New item → Lakehouse**, name it `bc_reporting`.
3. In the lakehouse, right-click **Files → Upload → Upload folder** and pick `data/bc_export/deltas`.
   You should now see `Files/deltas/Customer-18`, `CustLedgerEntry-21`, `DetailedCustLedgEntry-379`, `BankAccountLedgerEntry-271`, `GLEntry-17`.

## 3. Load the tables

1. **Open notebook → Import notebook** → `fabric/01_load_bc_export.ipynb`, attach it to `bc_reporting`.
2. **Run all.** It creates `Customer_18`, `CustLedgerEntry_21`, ... plus `company_map`, and enables change data feed on the source tables.

## 4. Create the AX views

1. Switch the lakehouse view to **SQL analytics endpoint** → **New SQL query**.
2. Paste and run each file of `sql/ax_compat/` in order: `00_schema.sql`, then `01` to `06` (one view per run).
3. Run `sql/ax_compat/checks.sql` and compare the numbers with [`reports/ax_views_reconciliation.md`](../reports/ax_views_reconciliation.md).

## 5. Screenshots for the README (save to `docs/img/fabric/`)

| File | What to capture |
|---|---|
| `01-lakehouse-files.png` | Lakehouse explorer with `Files/deltas/...` expanded and a Delta folder preview |
| `02-lakehouse-tables.png` | `Tables` expanded, `CustLedgerEntry_21` preview showing BC column names (`EntryNo-1`, `$Company`) |
| `03-notebook-run.png` | The notebook after *Run all*: the table/row-count output |
| `04-sql-view.png` | SQL analytics endpoint with `02_custtrans.sql` open in the editor |
| `05-ax-query.png` | Query 4 of `checks.sql` (overdue receivables by branch) with results |
| `06-dq-check.png` | `SELECT * FROM ax.DQ_UNMAPPED_COMPANIES` showing only the sandbox company |

Before publishing, check each screenshot: workspace and item names should be your portfolio names, and no other workspaces, tenants or e-mail addresses should be visible.
