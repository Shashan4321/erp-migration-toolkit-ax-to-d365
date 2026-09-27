"""AX-compatible views on the BC export: valid T-SQL, correct logic, and caught failure modes."""

import pandas as pd
import pytest
import sqlglot

from erpmig import ax_views, bc_export


@pytest.fixture(scope="module")
def tables():
    return bc_export.generate()


def test_every_view_file_is_valid_tsql_with_one_view():
    files = ax_views.view_files()
    assert len(files) == 6
    for path in files:
        sql = path.read_text(encoding="utf-8")
        assert sql.upper().count("CREATE OR ALTER VIEW") == 1, path.name
        sqlglot.parse(sql, read="tsql")  # raises on a syntax error


def test_all_reconciliation_checks_pass(tables):
    checks = ax_views.reconcile(ax_views.connect(tables))
    assert checks["passed"].all(), checks[~checks["passed"]].to_string()


def test_ax_columns_and_company_codes(tables):
    con = ax_views.connect(tables)
    cols = [r[0] for r in con.execute("DESCRIBE ax.CUSTTRANS").fetchall()]
    for col in [
        "ACCOUNTNUM",
        "DATAAREAID",
        "TRANSDATE",
        "VOUCHER",
        "AMOUNTCUR",
        "DIMENSION",
        "DIMENSION2_",
    ]:
        assert col in cols
    codes = {r[0] for r in con.execute("SELECT DISTINCT DATAAREAID FROM ax.CUSTTRANS").fetchall()}
    assert codes == {"cgl", "cin"}


def test_open_items_match_bc_open_flag(tables):
    con = ax_views.connect(tables)
    open_ax = {r[0] for r in con.execute("SELECT REFRECID FROM ax.CUSTTRANSOPEN").fetchall()}
    cle = tables["CustLedgerEntry-21"]
    mapped = cle["$Company"].isin(bc_export.COMPANIES)
    assert open_ax == set(cle.loc[mapped & cle["Open-36"], "EntryNo-1"])


def test_duplicate_company_mapping_is_caught(tables):
    """A company mapped twice doubles every row; the reconciliation must fail, not the report."""
    doubled = pd.concat([bc_export.company_map(), bc_export.company_map().head(1)])
    checks = ax_views.reconcile(ax_views.connect(tables, company_map=doubled)).set_index("check")
    assert not checks.loc["company_map has one row per company", "passed"]
    assert not checks.loc["CUSTTRANS rows = mapped Cust. Ledger Entry rows", "passed"]
    assert not checks.loc["CUSTTRANS AMOUNTCUR = detailed 'Initial Entry' amounts", "passed"]


def test_missing_mapping_is_reported_not_nulled(tables):
    only_global = bc_export.company_map().head(1)
    con = ax_views.connect(tables, company_map=only_global)
    unmapped = {
        r[0] for r in con.execute("SELECT CompanyName FROM ax.DQ_UNMAPPED_COMPANIES").fetchall()
    }
    assert unmapped == {"Contoso India Pvt. Ltd.", bc_export.UNMAPPED_COMPANY}
    assert (
        con.execute("SELECT COUNT(*) FROM ax.CUSTTRANS WHERE DATAAREAID IS NULL").fetchone()[0] == 0
    )


def test_delta_export_round_trip(tmp_path):
    from deltalake import DeltaTable

    written = bc_export.write(tmp_path)
    folder = tmp_path / "deltas" / "CustLedgerEntry-21"
    back = DeltaTable(str(folder)).to_pandas()
    assert len(back) == len(written["CustLedgerEntry-21"])
    assert {"EntryNo-1", "CustomerNo-3", "$Company"} <= set(back.columns)
    assert (tmp_path / "csv" / "company_map.csv").exists()


def test_fabric_checks_script_runs(tables):
    """sql/ax_compat/checks.sql (run by hand in Fabric) must also run here and give sane results."""
    con = ax_views.connect(tables)
    script = (ax_views.SQL_DIR / "checks.sql").read_text(encoding="utf-8")
    results = [con.execute(s).df() for s in sqlglot.transpile(script, read="tsql", write="duckdb")]
    assert len(results) == 4
    assert results[0]["CompanyName"].unique().tolist() == [bc_export.UNMAPPED_COMPANY]
    assert results[2]["net"].abs().max() < 0.01
    assert results[3]["overdue_amount"].gt(0).all()


def test_fabric_notebook_is_valid_json():
    import json

    nb = json.loads(
        (ax_views.ROOT / "fabric" / "01_load_bc_export.ipynb").read_text(encoding="utf-8")
    )
    code = "".join("".join(c["source"]) for c in nb["cells"] if c["cell_type"] == "code")
    assert "saveAsTable" in code and "company_map" in code and "enableChangeDataFeed" in code
