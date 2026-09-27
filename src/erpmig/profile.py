"""Source data profiling: the first thing to run on any migration.

Produces ``reports/profiling.md`` with, per table and column: row count, null %,
distinct count, a sample value, and flagged issues (whitespace, mixed case,
invalid e-mails, duplicate keys after normalisation).
"""

from __future__ import annotations

from pathlib import Path

import pandas as pd

from .migrate import ROOT
from .rules import EMAIL_RE

KEYS = {
    "CUSTTABLE": "ACCOUNTNUM",
    "VENDTABLE": "ACCOUNTNUM",
    "INVENTTABLE": "ITEMID",
    "CUSTTRANSOPEN": "RECID",
}


def profile_table(name: str, df: pd.DataFrame) -> tuple[pd.DataFrame, list[str]]:
    rows, issues = [], []
    for col in df.columns:
        s = df[col]
        text = s.dropna().astype(str)
        flags = []
        if (text != text.str.strip()).any():
            flags.append(f"{int((text != text.str.strip()).sum())} with leading/trailing spaces")
        if col.endswith("GROUP") and (text.str.strip() != text.str.strip().str.upper()).any():
            flags.append("mixed case codes")
        if "EMAIL" in col:
            bad = int((~text.str.match(EMAIL_RE)).sum())
            if bad:
                flags.append(f"{bad} invalid e-mails")
        rows.append(
            {
                "column": col,
                "null_pct": round(100 * s.isna().mean(), 1),
                "distinct": int(s.nunique()),
                "sample": text.iloc[0] if len(text) else "",
                "flags": "; ".join(flags),
            }
        )
        issues += [f"{name}.{col}: {f}" for f in flags]
        if s.isna().any() and col in {"CURRENCY", "UNITID", "CURRENCYCODE"}:
            issues.append(f"{name}.{col}: {int(s.isna().sum())} missing values")
    if name in KEYS:
        k = df[KEYS[name]].astype(str).str.strip().str.upper()
        d = int(k.duplicated().sum())
        if d:
            issues.append(f"{name}.{KEYS[name]}: {d} duplicate keys after trim/upper")
    return pd.DataFrame(rows), issues


def run(source_dir: Path = ROOT / "data" / "source_ax", out: Path = ROOT / "reports") -> Path:
    out.mkdir(parents=True, exist_ok=True)
    lines = ["# Source data profiling (synthetic AX extract)", ""]
    all_issues: list[str] = []
    for csv in sorted(source_dir.glob("*.csv")):
        df = pd.read_csv(csv, dtype=str)
        prof, issues = profile_table(csv.stem, df)
        all_issues += issues
        lines += [f"## {csv.stem} ({len(df):,} rows)", "", prof.to_markdown(index=False), ""]
    lines[2:2] = ["## Issues found", ""] + [f"- {i}" for i in all_issues] + [""]
    path = out / "profiling.md"
    path.write_text("\n".join(lines))
    return path


if __name__ == "__main__":
    print(f"Profiling report -> {run()}")
