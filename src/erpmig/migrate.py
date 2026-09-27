"""Extract -> transform -> load (to BC-ready files) driven by ``mappings/entities.yaml``.

Every source row ends up in exactly one of two places:

* ``data/target_bc/<entity>.csv``  - ready for a Business Central configuration package
* ``data/rejects/<entity>.csv``    - with a machine-readable ``reject_reason``

That "accounted for exactly once" property is what the reconciliation step proves.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path

import pandas as pd
import yaml

from .rules import apply_rules

ROOT = Path(__file__).resolve().parents[2]
ORDER = ["customer", "vendor", "item", "open_invoice", "gl_opening_balance"]  # FK order


@dataclass
class EntityResult:
    entity: str
    source_rows: int
    loaded: pd.DataFrame
    rejects: pd.DataFrame
    warnings: list[str] = field(default_factory=list)


def load_spec(path: Path = ROOT / "mappings" / "entities.yaml") -> dict:
    return yaml.safe_load(path.read_text())


def transform_entity(
    name: str, spec: dict, source: pd.DataFrame, loaded: dict[str, pd.DataFrame]
) -> EntityResult:
    src = source.reset_index(drop=True)
    out = pd.DataFrame(index=src.index)
    warnings: list[str] = []
    for target_col, f in spec["fields"].items():
        col = src[f["from"]]
        if f["from"] == "CURRENCY" or f["from"] == "CURRENCYCODE":
            n_missing = int(col.isna().sum())
            if n_missing:
                warnings.append(f"{n_missing} rows had no currency; defaulted to local currency")
        out[target_col] = apply_rules(col, f.get("rules", []))
    out["_source_row"] = src.index

    reasons = pd.Series("", index=out.index, dtype="string")

    # 1. required fields
    for col in spec.get("required", []):
        bad = out[col].isna() | (out[col].astype("string").str.len() == 0)
        reasons = reasons.mask(bad & (reasons == ""), f"missing_required:{col}")

    # 2. duplicates after normalisation (keep first occurrence)
    if spec.get("dedupe_on"):
        dup = out.duplicated(subset=spec["dedupe_on"], keep="first")
        reasons = reasons.mask(dup & (reasons == ""), "duplicate_after_normalisation")

    # 3. referential integrity against entities loaded earlier
    for col, parent in spec.get("foreign_keys", {}).items():
        parent_keys = set(loaded[parent]["No."])
        orphan = ~out[col].isin(parent_keys)
        reasons = reasons.mask(orphan & (reasons == ""), f"orphan:{col}")

    ok = reasons == ""
    rejects = src.loc[~ok].copy()
    rejects["reject_reason"] = reasons[~ok].to_numpy()
    return EntityResult(name, len(src), out.loc[ok].reset_index(drop=True), rejects, warnings)


def run(
    source_dir: Path = ROOT / "data" / "source_ax",
    target_dir: Path = ROOT / "data" / "target_bc",
    reject_dir: Path = ROOT / "data" / "rejects",
) -> dict[str, EntityResult]:
    spec = load_spec()
    target_dir.mkdir(parents=True, exist_ok=True)
    reject_dir.mkdir(parents=True, exist_ok=True)
    results: dict[str, EntityResult] = {}
    loaded: dict[str, pd.DataFrame] = {}
    for name in ORDER:
        s = spec[name]
        source = pd.read_csv(source_dir / f"{s['source']}.csv", dtype=str, keep_default_na=True)
        for f in s["fields"].values():  # numeric columns back to numbers
            if "to_decimal" in f.get("rules", []) or f["from"] in {"BLOCKED", "RECID"}:
                source[f["from"]] = pd.to_numeric(source[f["from"]])
        res = transform_entity(name, s, source, loaded)
        loaded[name] = res.loaded
        res.loaded.drop(columns="_source_row").to_csv(target_dir / f"{name}.csv", index=False)
        res.rejects.to_csv(reject_dir / f"{name}.csv", index=False)
        results[name] = res
    return results


if __name__ == "__main__":
    for r in run().values():
        print(
            f"{r.entity:20s} source={r.source_rows:>5}  loaded={len(r.loaded):>5}  "
            f"rejected={len(r.rejects):>3}"
        )
