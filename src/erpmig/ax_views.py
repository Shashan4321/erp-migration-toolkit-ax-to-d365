"""Run the AX-compatible T-SQL views locally and reconcile them against the BC export.

The views in ``sql/ax_compat/`` are written in T-SQL for the Fabric SQL analytics endpoint.
Here they are transpiled with sqlglot and executed on DuckDB over the same synthetic tables,
so CI proves the logic before anything is deployed:

    python -m erpmig.ax_views          # -> reports/ax_views_reconciliation.md (exit 1 on failure)
"""

from __future__ import annotations

import re
import sys
from pathlib import Path

import duckdb
import pandas as pd
import sqlglot

from erpmig import bc_export

ROOT = Path(__file__).resolve().parents[2]
SQL_DIR = ROOT / "sql" / "ax_compat"
REPORT = ROOT / "reports" / "ax_views_reconciliation.md"
VIEWS = ["CUSTTABLE", "CUSTTRANS", "CUSTTRANSOPEN", "BANKACCOUNTTRANS", "LEDGERTRANS"]
TOL = 0.01


def view_files() -> list[Path]:
    """The numbered view scripts 01..NN (00 creates the schema, checks.sql is run by hand)."""
    return sorted(p for p in SQL_DIR.glob("[0-9][0-9]_*.sql") if not p.name.startswith("00_"))


def to_duckdb(tsql: str) -> str:
    """CREATE OR ALTER VIEW (T-SQL) -> CREATE OR REPLACE VIEW (DuckDB), brackets -> quotes."""
    tsql = re.sub(r"CREATE\s+OR\s+ALTER\s+VIEW", "CREATE VIEW", tsql, flags=re.I)
    duck = sqlglot.transpile(tsql, read="tsql", write="duckdb")[0]
    return re.sub(r"^CREATE VIEW", "CREATE OR REPLACE VIEW", duck)


def connect(
    tables: dict[str, pd.DataFrame] | None = None, company_map: pd.DataFrame | None = None
) -> duckdb.DuckDBPyConnection:
    """Load the BC export into schema dbo (Table-Id -> Table_Id, as in Fabric) and create ax.* views."""
    tables = tables if tables is not None else bc_export.generate()
    company_map = company_map if company_map is not None else bc_export.company_map()
    con = duckdb.connect()
    con.execute("CREATE SCHEMA dbo; CREATE SCHEMA ax;")
    for name, df in {**tables, "company_map": company_map}.items():
        con.register("tmp", df)
        con.execute(f'CREATE TABLE dbo."{name.replace("-", "_")}" AS SELECT * FROM tmp')
        con.unregister("tmp")
    for path in view_files():
        con.execute(to_duckdb(path.read_text(encoding="utf-8")))
    return con


def _by_company(con, sql: str) -> dict[str, float]:
    out = {k: round(float(v), 2) for k, v in con.execute(sql).fetchall()}
    return {k: int(v) if v.is_integer() else v for k, v in out.items()}


def _match(a: dict, b: dict) -> bool:
    return a.keys() == b.keys() and all(abs(a[k] - b[k]) <= TOL for k in a)


def reconcile(con: duckdb.DuckDBPyConnection) -> pd.DataFrame:
    """Each check compares an ax.* view with the BC source it is built from, per company."""
    # The source side uses a de-duplicated mapping, so a duplicated company_map row (which doubles
    # every view row) shows up as a mismatch instead of inflating both sides equally.
    mapped = (
        "JOIN (SELECT DISTINCT CompanyName, DATAAREAID FROM dbo.company_map) m "
        'ON m.CompanyName = s."$Company"'
    )
    checks: list[tuple[str, str, str, bool]] = []

    dupes = con.execute(
        "SELECT COUNT(*) FROM (SELECT CompanyName FROM dbo.company_map GROUP BY 1 HAVING COUNT(*) > 1)"
    ).fetchone()[0]
    checks.append(("company_map has one row per company", str(dupes), "0", dupes == 0))

    def add(name: str, view: dict, source: dict) -> None:
        checks.append((name, str(view), str(source), _match(view, source)))

    add(
        "CUSTTABLE rows = mapped Customer rows",
        _by_company(con, "SELECT DATAAREAID, COUNT(*) FROM ax.CUSTTABLE GROUP BY 1"),
        _by_company(
            con, f"SELECT m.DATAAREAID, COUNT(*) FROM dbo.Customer_18 s {mapped} GROUP BY 1"
        ),
    )
    add(
        "CUSTTRANS rows = mapped Cust. Ledger Entry rows",
        _by_company(con, "SELECT DATAAREAID, COUNT(*) FROM ax.CUSTTRANS GROUP BY 1"),
        _by_company(
            con, f"SELECT m.DATAAREAID, COUNT(*) FROM dbo.CustLedgerEntry_21 s {mapped} GROUP BY 1"
        ),
    )
    add(
        "CUSTTRANS AMOUNTCUR = detailed 'Initial Entry' amounts",
        _by_company(con, "SELECT DATAAREAID, SUM(AMOUNTCUR) FROM ax.CUSTTRANS GROUP BY 1"),
        _by_company(
            con,
            f'SELECT m.DATAAREAID, SUM(s."Amount-7") FROM dbo.DetailedCustLedgEntry_379 s {mapped} '
            "WHERE s.\"EntryType-3\" = 'Initial Entry' GROUP BY 1",
        ),
    )
    add(
        "CUSTTRANSOPEN balance = sum of all detailed entries (open AR)",
        _by_company(con, "SELECT DATAAREAID, SUM(AMOUNTCUR) FROM ax.CUSTTRANSOPEN GROUP BY 1"),
        _by_company(
            con,
            f'SELECT m.DATAAREAID, SUM(s."Amount-7") FROM dbo.DetailedCustLedgEntry_379 s {mapped} GROUP BY 1',
        ),
    )
    add(
        "CUSTTRANSOPEN items = BC entries flagged Open",
        _by_company(con, "SELECT DATAAREAID, COUNT(*) FROM ax.CUSTTRANSOPEN GROUP BY 1"),
        _by_company(
            con,
            f'SELECT m.DATAAREAID, COUNT(*) FROM dbo.CustLedgerEntry_21 s {mapped} WHERE s."Open-36" GROUP BY 1',
        ),
    )
    add(
        "BANKACCOUNTTRANS amount = Bank Account Ledger Entry amount",
        _by_company(con, "SELECT DATAAREAID, SUM(AMOUNTCUR) FROM ax.BANKACCOUNTTRANS GROUP BY 1"),
        _by_company(
            con,
            f'SELECT m.DATAAREAID, SUM(s."Amount-13") FROM dbo.BankAccountLedgerEntry_271 s {mapped} GROUP BY 1',
        ),
    )
    ledger = _by_company(con, "SELECT DATAAREAID, SUM(AMOUNTMST) FROM ax.LEDGERTRANS GROUP BY 1")
    add("LEDGERTRANS nets to zero per company (double entry)", ledger, dict.fromkeys(ledger, 0.0))

    nulls = sum(
        con.execute(f"SELECT COUNT(*) FROM ax.{v} WHERE DATAAREAID IS NULL").fetchone()[0]
        for v in VIEWS
    )
    checks.append(("No NULL DATAAREAID in any ax.* view", str(nulls), "0", nulls == 0))

    unmapped = sorted(
        {r[0] for r in con.execute("SELECT CompanyName FROM ax.DQ_UNMAPPED_COMPANIES").fetchall()}
    )
    expected = [bc_export.UNMAPPED_COMPANY]
    checks.append(
        (
            "DQ view reports the unmapped sandbox company",
            str(unmapped),
            str(expected),
            unmapped == expected,
        )
    )

    return pd.DataFrame(checks, columns=["check", "ax_view", "bc_source", "passed"])


def write_report(checks: pd.DataFrame, con: duckdb.DuckDBPyConnection, path: Path = REPORT) -> None:
    counts = {v: con.execute(f"SELECT COUNT(*) FROM ax.{v}").fetchone()[0] for v in VIEWS}
    dq = con.execute("SELECT * FROM ax.DQ_UNMAPPED_COMPANIES ORDER BY 1").df()
    lines = [
        "# AX-compatible views: reconciliation",
        "",
        "Output of `python -m erpmig.ax_views`: the T-SQL views in `sql/ax_compat/` run on the synthetic",
        "BC export and are compared with the source tables, per company (DATAAREAID).",
        "",
        f"**{int(checks['passed'].sum())}/{len(checks)} checks pass.**",
        "",
        checks.assign(passed=checks["passed"].map({True: "✅", False: "❌"})).to_markdown(
            index=False
        ),
        "",
        "## View row counts",
        "",
        pd.DataFrame(counts.items(), columns=["view", "rows"]).to_markdown(index=False),
        "",
        "## ax.DQ_UNMAPPED_COMPANIES",
        "",
        dq.to_markdown(index=False),
        "",
    ]
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("\n".join(lines), encoding="utf-8")


def main() -> int:
    con = connect()
    checks = reconcile(con)
    write_report(checks, con)
    print(checks.to_string(index=False))
    return 0 if checks["passed"].all() else 1


if __name__ == "__main__":
    sys.exit(main())
