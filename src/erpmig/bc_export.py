"""Synthetic Business Central export in the bc2adls layout, for post-go-live reporting on Fabric.

After the AX -> BC cut-over, BC tables are exported to a Microsoft Fabric lakehouse as Delta
folders (the open-source *bc2adls* convention: ``deltas/<Table>-<TableId>/``, columns named
``<Field>-<FieldId>`` plus ``$Company``). The views in ``sql/ax_compat/`` then expose them
with AX column names so the old AX reports keep running.

Everything is generated from a fixed seed for two invented companies. Field IDs follow the
BC naming pattern and are illustrative; no employer or client data is used.

    python -m erpmig.bc_export            # -> data/bc_export/deltas/*  and  data/bc_export/csv/*
"""

from __future__ import annotations

from pathlib import Path

import numpy as np
import pandas as pd
from faker import Faker

ROOT = Path(__file__).resolve().parents[2]
OUT = ROOT / "data" / "bc_export"
SEED = 11

COMPANIES = {
    # BC company name -> AX DATAAREAID, used by dbo.company_map
    "Contoso Global Ltd.": "cgl",
    "Contoso India Pvt. Ltd.": "cin",
}
# A sandbox company that exists in BC but was never mapped: the data-quality view must catch it.
UNMAPPED_COMPANY = "CRONUS Test Sandbox"

POSTING_GROUPS = ["DOMESTIC", "EXPORT", "INTERCO"]
BRANCHES = ["DEL", "MUM", "BLR", "HYD", "DXB"]
DEPARTMENTS = ["SALES", "RETAIL", "ONLINE", "B2B"]
BANKS = ["B0010", "B0018", "B0028"]
GL_ACCOUNTS = {"40100": "Sales", "13100": "Receivables", "27100": "Bank", "56100": "Bank charges"}


def _dates(rng: np.random.Generator, n: int, start: str, end: str) -> pd.Series:
    days = pd.date_range(start, end, freq="D")
    return pd.Series(rng.choice(days.to_numpy(), n)).dt.normalize()


def generate(n_customers: int = 180, invoices_per_company: int = 1500) -> dict[str, pd.DataFrame]:
    """Return every exported table as a DataFrame, keyed by bc2adls folder name."""
    rng = np.random.default_rng(SEED)
    fake = Faker("en_IN")
    Faker.seed(SEED)

    customers, cle, dcle, bank, gl = [], [], [], [], []
    entry = {"cle": 100_000, "dcle": 500_000, "bank": 160_000, "gl": 900_000}
    companies = [*COMPANIES, UNMAPPED_COMPANY]

    for company in companies:
        small = company == UNMAPPED_COMPANY
        n_cust = 5 if small else n_customers
        n_inv = 20 if small else invoices_per_company
        prefix = "SB" if small else company.split()[1][:2].upper()  # GL / IN / SB

        cust = pd.DataFrame(
            {
                "No-1": [f"C{prefix}{i:05d}" for i in range(1, n_cust + 1)],
                "Name-2": [fake.company().upper() for _ in range(n_cust)],
                "CustomerPostingGroup-21": rng.choice(POSTING_GROUPS, n_cust, p=[0.7, 0.2, 0.1]),
                "CurrencyCode-22": rng.choice(["", "", "", "USD", "AED"], n_cust),
                "CountryRegionCode-35": "IN",
                "Blocked-39": rng.choice(["", "", "", "", "Invoice"], n_cust),
                "$Company": company,
            }
        )
        customers.append(cust)

        # Invoices, and payments against ~80% of them
        inv_cust = cust.sample(n_inv, replace=True, random_state=int(rng.integers(1e9)))
        inv_date = _dates(rng, n_inv, "2025-04-01", "2026-09-15")
        amount = (rng.lognormal(10.2, 0.7, n_inv)).round(2)
        for i in range(n_inv):
            c = inv_cust.iloc[i]
            entry["cle"] += 1
            inv_no = entry["cle"]
            doc = f"SI-{prefix}-{inv_no}"
            post = inv_date.iloc[i]
            paid = rng.random() < 0.8
            cle.append(
                {
                    "EntryNo-1": inv_no,
                    "CustomerNo-3": c["No-1"],
                    "PostingDate-4": post,
                    "DocumentType-5": "Invoice",
                    "DocumentNo-6": doc,
                    "Description-7": f"Invoice {doc}",
                    "CustomerName-8": c["Name-2"],
                    "CurrencyCode-11": c["CurrencyCode-22"],
                    "CustomerPostingGroup-22": c["CustomerPostingGroup-21"],
                    "GlobalDimension1Code-23": rng.choice(BRANCHES),
                    "GlobalDimension2Code-24": rng.choice(DEPARTMENTS),
                    "Open-36": not paid,
                    "DueDate-37": post + pd.Timedelta(days=30),
                    "DocumentDate-62": post,
                    "$Company": company,
                }
            )
            entry["dcle"] += 1
            dcle.append(
                _detail(
                    entry["dcle"],
                    inv_no,
                    "Initial Entry",
                    post,
                    "Invoice",
                    doc,
                    amount[i],
                    c,
                    company,
                )
            )
            gl += _gl_pair(entry, post, doc, amount[i], "40100", "13100", f"Invoice {doc}", company)

            if paid:
                entry["cle"] += 1
                pay_no = entry["cle"]
                pay_date = post + pd.Timedelta(days=int(rng.integers(5, 60)))
                pay_doc = f"BR-{prefix}-{pay_no}"
                bank_no = rng.choice(BANKS)
                cle.append(
                    {
                        **cle[-1],
                        "EntryNo-1": pay_no,
                        "PostingDate-4": pay_date,
                        "DocumentType-5": "Payment",
                        "DocumentNo-6": pay_doc,
                        "Description-7": c["Name-2"],
                        "Open-36": False,
                        "DueDate-37": pay_date,
                        "DocumentDate-62": pay_date,
                    }
                )
                cle[-2]["Open-36"] = False
                entry["dcle"] += 1
                dcle.append(
                    _detail(
                        entry["dcle"],
                        pay_no,
                        "Initial Entry",
                        pay_date,
                        "Payment",
                        pay_doc,
                        -amount[i],
                        c,
                        company,
                    )
                )
                entry["dcle"] += 1  # application: closes the invoice
                dcle.append(
                    _detail(
                        entry["dcle"],
                        inv_no,
                        "Application",
                        pay_date,
                        "Payment",
                        pay_doc,
                        -amount[i],
                        c,
                        company,
                    )
                )
                entry["dcle"] += 1
                dcle.append(
                    _detail(
                        entry["dcle"],
                        pay_no,
                        "Application",
                        pay_date,
                        "Payment",
                        pay_doc,
                        amount[i],
                        c,
                        company,
                    )
                )
                entry["bank"] += 1
                bank.append(
                    {
                        "EntryNo-1": entry["bank"],
                        "BankAccountNo-3": bank_no,
                        "PostingDate-4": pay_date,
                        "DocumentType-5": "Payment",
                        "DocumentNo-6": pay_doc,
                        "Description-7": c["Name-2"],
                        "CurrencyCode-11": c["CurrencyCode-22"],
                        "Amount-13": amount[i],
                        "Open-36": bool(
                            rng.random() < 0.05
                        ),  # not yet reconciled with the statement
                        "$Company": company,
                    }
                )
                gl += _gl_pair(
                    entry, pay_date, pay_doc, amount[i], "13100", "27100", c["Name-2"], company
                )

    tables = {
        "Customer-18": pd.DataFrame(pd.concat(customers, ignore_index=True)),
        "CustLedgerEntry-21": pd.DataFrame(cle),
        "DetailedCustLedgEntry-379": pd.DataFrame(dcle),
        "BankAccountLedgerEntry-271": pd.DataFrame(bank),
        "GLEntry-17": pd.DataFrame(gl),
    }
    for df in tables.values():
        df["SystemModifiedAt-2000000003"] = pd.Timestamp("2026-09-20 02:00:00")
    return tables


def _detail(no, cle_no, etype, date, dtype, doc, amount, cust, company) -> dict:
    return {
        "EntryNo-1": no,
        "CustLedgerEntryNo-2": cle_no,
        "EntryType-3": etype,
        "PostingDate-4": date,
        "DocumentType-5": dtype,
        "DocumentNo-6": doc,
        "Amount-7": round(float(amount), 2),
        "CustomerNo-9": cust["No-1"],
        "CurrencyCode-12": cust["CurrencyCode-22"],
        "$Company": company,
    }


def _gl_pair(entry: dict, date, doc, amount, credit_acc, debit_acc, text, company) -> list[dict]:
    """A balanced double entry: debit one account, credit another."""
    rows = []
    for acc, amt in ((debit_acc, amount), (credit_acc, -amount)):
        entry["gl"] += 1
        rows.append(
            {
                "EntryNo-1": entry["gl"],
                "GLAccountNo-3": acc,
                "PostingDate-4": date,
                "DocumentNo-6": doc,
                "Description-7": text,
                "Amount-17": round(float(amt), 2),
                "$Company": company,
            }
        )
    return rows


def company_map() -> pd.DataFrame:
    return pd.DataFrame({"CompanyName": list(COMPANIES), "DATAAREAID": list(COMPANIES.values())})


def write(out: Path = OUT, delta: bool = True) -> dict[str, pd.DataFrame]:
    """Write CSVs (for local tests) and, by default, Delta folders (to upload to Fabric)."""
    tables = generate()
    (out / "csv").mkdir(parents=True, exist_ok=True)
    for name, df in {**tables, "company_map": company_map()}.items():
        df.to_csv(out / "csv" / f"{name}.csv", index=False)
    if delta:
        from deltalake import write_deltalake

        for name, df in tables.items():
            write_deltalake(str(out / "deltas" / name), df, mode="overwrite")
    return tables


if __name__ == "__main__":
    written = write()
    for name, df in written.items():
        print(f"{name:<28} {len(df):>7,} rows")
    print(f"-> {OUT}")
