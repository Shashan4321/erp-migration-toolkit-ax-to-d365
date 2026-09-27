"""Vectorised cleansing / transformation rules referenced by the mapping YAML."""

from __future__ import annotations

from collections.abc import Callable

import pandas as pd

LCY = "INR"  # local currency: Business Central stores it as a blank Currency Code
EMAIL_RE = r"^[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}$"
POSTING_GROUPS = {"DOM": "DOMESTIC", "EXP": "EXPORT", "INTERCO": "INTERCOMPANY", "RETAIL": "RETAIL"}
BLOCKED = {0: "", 1: "Invoice", 2: "All"}

Rule = Callable[[pd.Series], pd.Series]


def _str(s: pd.Series) -> pd.Series:
    return s.astype("string")


RULES: dict[str, Rule] = {
    "trim": lambda s: _str(s).str.strip(),
    "upper": lambda s: _str(s).str.upper(),
    "lower": lambda s: _str(s).str.lower(),
    "truncate_30": lambda s: _str(s).str.slice(0, 30),
    "truncate_100": lambda s: _str(s).str.slice(0, 100),
    "to_decimal": lambda s: pd.to_numeric(s, errors="coerce").round(2),
    "lcy_blank": lambda s: _str(s).where(_str(s) != LCY, "").fillna(""),
    "valid_email_or_blank": lambda s: _str(s).where(_str(s).str.match(EMAIL_RE, na=False), ""),
    "map_posting_group": lambda s: _str(s).map(POSTING_GROUPS).astype("string"),
    "map_blocked": lambda s: s.map(BLOCKED).fillna(""),
    "default_pcs": lambda s: _str(s).fillna("PCS").replace("", "PCS"),
}


def apply_rules(series: pd.Series, rules: list[str]) -> pd.Series:
    for name in rules:
        if name not in RULES:
            raise KeyError(f"Unknown rule '{name}' in mapping spec")
        series = RULES[name](series)
    return series
