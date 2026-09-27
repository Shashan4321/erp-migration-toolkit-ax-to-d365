"""Reconciliation: prove that nothing was lost or changed in flight.

Checks per entity
-----------------
1. **Row accounting** - source rows = loaded rows + rejected rows (nothing silently dropped).
2. **Key checksum** - MD5 over the sorted, normalised business keys of source vs target
   (+ rejects). Catches keys that were altered, not just counts that happen to match.
3. **Financial totals** - open-invoice amounts per currency and the G/L trial balance
   must match to the paisa: target + rejected = source.
4. **Trial balance** - G/L opening balances must net to zero in the target.

Writes ``reports/reconciliation.md`` and ``reports/reconciliation.json``; exits 1 on failure
so it can gate a cut-over in CI.
"""

from __future__ import annotations

import hashlib
import json
import sys
from dataclasses import asdict, dataclass
from pathlib import Path

import pandas as pd

from .migrate import ROOT, EntityResult, load_spec, run


@dataclass
class Check:
    entity: str
    check: str
    source: str
    target: str
    passed: bool


def _md5(values: pd.Series) -> str:
    joined = "\n".join(sorted(values.astype(str)))
    return hashlib.md5(joined.encode()).hexdigest()[:12]


def reconcile(results: dict[str, EntityResult]) -> list[Check]:
    spec = load_spec()
    checks: list[Check] = []
    for name, r in results.items():
        s = spec[name]
        # 1. row accounting
        accounted = len(r.loaded) + len(r.rejects)
        checks.append(
            Check(
                name,
                "row accounting (loaded + rejected)",
                f"{r.source_rows:,}",
                f"{len(r.loaded):,} + {len(r.rejects):,}",
                bool(accounted == r.source_rows),
            )
        )

        # 2. key checksum: normalise source keys the same way as the target key
        key = s["key"]
        if isinstance(key["source"], str):
            src_col = pd.read_csv(ROOT / "data" / "source_ax" / f"{s['source']}.csv", dtype=str)[
                key["source"]
            ]
            key_rules = s["fields"][key["target"]].get("rules", [])
            from .rules import apply_rules

            src_keys = apply_rules(src_col, key_rules)
            tgt_keys = pd.concat(
                [
                    r.loaded[key["target"]],
                    apply_rules(r.rejects[key["source"]].astype(str), key_rules),
                ]
            )
            checks.append(
                Check(
                    name,
                    "key checksum (MD5)",
                    _md5(src_keys),
                    _md5(tgt_keys),
                    bool(_md5(src_keys) == _md5(tgt_keys)),
                )
            )

    # 3. financial totals: open invoices per currency
    inv = results["open_invoice"]
    src = pd.read_csv(ROOT / "data" / "source_ax" / "CUSTTRANSOPEN.csv")
    src["cur"] = src["CURRENCYCODE"].fillna("INR").replace("INR", "LCY")
    tgt = inv.loaded.assign(cur=inv.loaded["Currency Code"].replace("", "LCY"))
    rej = inv.rejects.assign(cur=inv.rejects["CURRENCYCODE"].fillna("INR").replace("INR", "LCY"))
    for cur, s_amt in src.groupby("cur")["AMOUNTCUR"].sum().round(2).items():
        t_amt = round(tgt.loc[tgt["cur"] == cur, "Amount"].sum(), 2)
        r_amt = round(pd.to_numeric(rej.loc[rej["cur"] == cur, "AMOUNTCUR"]).sum(), 2)
        checks.append(
            Check(
                "open_invoice",
                f"amount total {cur} (loaded + rejected)",
                f"{s_amt:,.2f}",
                f"{t_amt:,.2f} + {r_amt:,.2f}",
                bool(abs(s_amt - (t_amt + r_amt)) < 0.005),
            )
        )

    # 4. G/L: per-account totals and trial balance
    gl = results["gl_opening_balance"]
    gsrc = pd.read_csv(ROOT / "data" / "source_ax" / "LEDGERBALANCE.csv", dtype={"ACCOUNTNUM": str})
    by_src = gsrc.groupby("ACCOUNTNUM")["AMOUNTMST"].sum().round(2)
    by_tgt = gl.loaded.groupby("G/L Account No.")["Amount (LCY)"].sum().round(2)
    checks.append(
        Check(
            "gl_opening_balance",
            "per-account totals match",
            f"{len(by_src)} accounts",
            f"{int((by_src == by_tgt).sum())} match",
            bool(by_src.equals(by_tgt)),
        )
    )
    tb = round(gl.loaded["Amount (LCY)"].sum(), 2)
    checks.append(
        Check(
            "gl_opening_balance",
            "trial balance nets to zero",
            f"{round(gsrc['AMOUNTMST'].sum(), 2) + 0:,.2f}",
            f"{tb + 0:,.2f}",
            bool(abs(tb) < 0.005),
        )
    )
    return checks


def write_report(
    results: dict[str, EntityResult], checks: list[Check], out_dir: Path = ROOT / "reports"
) -> Path:
    out_dir.mkdir(parents=True, exist_ok=True)
    passed = sum(c.passed for c in checks)
    lines = [
        "# Migration reconciliation report",
        "",
        f"**Result: {'PASS' if passed == len(checks) else 'FAIL'}** - "
        f"{passed}/{len(checks)} checks passed.",
        "",
        "## Entity summary",
        "",
        "| Entity | Source | Loaded | Rejected | Warnings |",
        "|---|---:|---:|---:|---|",
    ]
    for r in results.values():
        lines.append(
            f"| {r.entity} | {r.source_rows:,} | {len(r.loaded):,} | "
            f"{len(r.rejects):,} | {'; '.join(r.warnings) or '-'} |"
        )
    lines += [
        "",
        "## Checks",
        "",
        "| Entity | Check | Source | Target | Result |",
        "|---|---|---|---|---|",
    ]
    lines += [
        f"| {c.entity} | {c.check} | {c.source} | {c.target} | {'✅' if c.passed else '❌'} |"
        for c in checks
    ]
    reasons = pd.concat([r.rejects.assign(entity=r.entity) for r in results.values()])
    if len(reasons):
        lines += [
            "",
            "## Rejects by reason (fix in source, then re-run)",
            "",
            "| Entity | Reason | Rows |",
            "|---|---|---:|",
        ]
        for (e, why), n in reasons.groupby(["entity", "reject_reason"]).size().items():
            lines.append(f"| {e} | `{why}` | {n} |")
    path = out_dir / "reconciliation.md"
    path.write_text("\n".join(lines) + "\n")
    (out_dir / "reconciliation.json").write_text(
        json.dumps(
            {"passed": passed, "total": len(checks), "checks": [asdict(c) for c in checks]},
            indent=2,
            default=str,
        )
    )
    return path


def main() -> int:
    results = run()
    checks = reconcile(results)
    path = write_report(results, checks)
    failed = [c for c in checks if not c.passed]
    print(f"{len(checks) - len(failed)}/{len(checks)} checks passed -> {path}")
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())
