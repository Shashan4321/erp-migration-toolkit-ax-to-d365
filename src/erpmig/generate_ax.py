"""Generate synthetic Dynamics AX 2012-style source extracts.

Column names follow the public AX data dictionary conventions (CUSTTABLE,
VENDTABLE, INVENTTABLE, CUSTTRANSOPEN, LEDGERTRANS), but every value is invented.
Realistic data-quality problems are injected on purpose, because a migration
toolkit is only worth something if it catches them:

* duplicate customers differing only by case / whitespace
* trailing spaces and mixed-case codes
* missing currency codes
* invalid e-mail addresses
* items with no unit of measure
* open invoices pointing at customers that do not exist (orphans)
"""

from __future__ import annotations

from pathlib import Path

import numpy as np
import pandas as pd
from faker import Faker

SEED = 7
CURRENCIES = ["INR", "INR", "INR", "USD", "AED"]
CUST_GROUPS = ["DOM", "EXP", "INTERCO", "RETAIL"]
ITEM_GROUPS = ["RAW", "FG", "SPARE", "PACK"]
UNITS = ["PCS", "KG", "BOX", "LTR"]
LEGAL_ENTITY = "demo"  # AX DATAAREAID


def _customers(fake: Faker, rng: np.random.Generator, n: int) -> pd.DataFrame:
    df = pd.DataFrame(
        {
            "ACCOUNTNUM": [f"C{i:05d}" for i in range(1, n + 1)],
            "NAME": [fake.company() for _ in range(n)],
            "CUSTGROUP": rng.choice(CUST_GROUPS, n),
            "CURRENCY": rng.choice(CURRENCIES, n),
            "EMAIL": [fake.company_email() for _ in range(n)],
            "CITY": [fake.city() for _ in range(n)],
            "CREDITMAX": rng.choice([0, 50000, 100000, 250000, 500000], n).astype(float),
            "BLOCKED": rng.choice([0, 0, 0, 0, 0, 0, 0, 0, 1, 2], n),  # 0 No, 1 Invoice, 2 All
            "DATAAREAID": LEGAL_ENTITY,
        }
    )
    # --- inject data-quality issues ---
    idx = rng.choice(n, 25, replace=False)
    df.loc[idx[:8], "CURRENCY"] = None  # missing currency
    df.loc[idx[8:16], "EMAIL"] = ["not-an-email"] * 8  # invalid email
    df.loc[idx[16:25], "CUSTGROUP"] = df.loc[idx[16:25], "CUSTGROUP"].str.lower() + "  "
    dups = df.sample(6, random_state=SEED).copy()  # case/space duplicates
    dups["ACCOUNTNUM"] = dups["ACCOUNTNUM"].str.lower() + " "
    return pd.concat([df, dups], ignore_index=True)


def _vendors(fake: Faker, rng: np.random.Generator, n: int) -> pd.DataFrame:
    return pd.DataFrame(
        {
            "ACCOUNTNUM": [f"V{i:05d}" for i in range(1, n + 1)],
            "NAME": [fake.company() for _ in range(n)],
            "VENDGROUP": rng.choice(["LOCAL", "IMPORT", "SERVICE"], n),
            "CURRENCY": rng.choice(CURRENCIES, n),
            "PAYMTERMID": rng.choice(["NET30", "NET45", "NET60", "COD"], n),
            "DATAAREAID": LEGAL_ENTITY,
        }
    )


def _items(fake: Faker, rng: np.random.Generator, n: int) -> pd.DataFrame:
    df = pd.DataFrame(
        {
            "ITEMID": [f"IT-{i:05d}" for i in range(1, n + 1)],
            "ITEMNAME": [f"{fake.word().title()} {fake.word()}" for _ in range(n)],
            "ITEMGROUPID": rng.choice(ITEM_GROUPS, n),
            "UNITID": rng.choice(UNITS, n),
            "PRICE": rng.uniform(10, 25000, n).round(2),
            "DATAAREAID": LEGAL_ENTITY,
        }
    )
    df.loc[rng.choice(n, 5, replace=False), "UNITID"] = None  # missing UoM
    return df


def _open_invoices(rng: np.random.Generator, customers: pd.DataFrame, n: int) -> pd.DataFrame:
    valid = customers["ACCOUNTNUM"].iloc[: len(customers) - 6].to_numpy()  # exclude dup rows
    accts = rng.choice(valid, n)
    accts[rng.choice(n, 4, replace=False)] = "C99999"  # orphans
    cur = customers.drop_duplicates("ACCOUNTNUM").set_index("ACCOUNTNUM")["CURRENCY"]
    return pd.DataFrame(
        {
            "RECID": np.arange(5_000_001, 5_000_001 + n),
            "ACCOUNTNUM": accts,
            "INVOICE": [f"INV-{i:06d}" for i in range(1, n + 1)],
            "TRANSDATE": (
                pd.Timestamp("2024-01-01") + pd.to_timedelta(rng.integers(0, 365, n), unit="D")
            ).date,
            "DUEDATE": None,
            "AMOUNTCUR": rng.uniform(500, 400000, n).round(2),
            "CURRENCYCODE": [cur.get(a) or "INR" for a in accts],
            "DATAAREAID": LEGAL_ENTITY,
        }
    )


def _gl_balances(rng: np.random.Generator) -> pd.DataFrame:
    accounts = {
        "110100": "Cash at bank",
        "120100": "Trade receivables",
        "140100": "Inventory",
        "210100": "Trade payables",
        "220100": "GST payable",
        "310100": "Share capital",
        "320100": "Retained earnings",
        "410100": "Revenue - domestic",
        "420100": "Revenue - export",
        "510100": "Cost of goods sold",
        "610100": "Salaries",
        "620100": "Rent",
        "630100": "Freight",
    }
    rows = []
    for acct, name in accounts.items():
        for dim in ["SALES", "OPS", "ADMIN"]:
            sign = 1 if acct[0] in "156" else -1
            rows.append(
                {
                    "ACCOUNTNUM": acct,
                    "ACCOUNTNAME": name,
                    "DEPARTMENT": dim,
                    "AMOUNTMST": round(sign * float(rng.uniform(1e5, 5e7)), 2),
                }
            )
    df = pd.DataFrame(rows)
    # force the trial balance to zero via retained earnings, like a real closed year
    plug = -df["AMOUNTMST"].sum()
    df.loc[(df["ACCOUNTNUM"] == "320100") & (df["DEPARTMENT"] == "ADMIN"), "AMOUNTMST"] += plug
    df["AMOUNTMST"] = df["AMOUNTMST"].round(2)
    df.loc[df.index[-1], "AMOUNTMST"] -= round(df["AMOUNTMST"].sum(), 2)
    df["DATAAREAID"] = LEGAL_ENTITY
    return df


def generate(out_dir: str | Path = "data/source_ax") -> dict[str, int]:
    """Write the AX extracts as CSV (like a BCP / SSIS export) and return row counts."""
    fake = Faker("en_IN")
    Faker.seed(SEED)
    rng = np.random.default_rng(SEED)
    out = Path(out_dir)
    out.mkdir(parents=True, exist_ok=True)
    customers = _customers(fake, rng, 600)
    tables = {
        "CUSTTABLE": customers,
        "VENDTABLE": _vendors(fake, rng, 150),
        "INVENTTABLE": _items(fake, rng, 400),
        "CUSTTRANSOPEN": _open_invoices(rng, customers, 1800),
        "LEDGERBALANCE": _gl_balances(rng),
    }
    for name, df in tables.items():
        df.to_csv(out / f"{name}.csv", index=False)
    return {k: len(v) for k, v in tables.items()}


if __name__ == "__main__":
    for t, n in generate().items():
        print(f"{t:15s} {n:>6,} rows")
