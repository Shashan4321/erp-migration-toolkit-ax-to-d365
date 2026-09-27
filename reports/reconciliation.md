# Migration reconciliation report

**Result: PASS** - 14/14 checks passed.

## Entity summary

| Entity | Source | Loaded | Rejected | Warnings |
|---|---:|---:|---:|---|
| customer | 606 | 600 | 6 | 8 rows had no currency; defaulted to local currency |
| vendor | 150 | 150 | 0 | - |
| item | 400 | 400 | 0 | - |
| open_invoice | 1,800 | 1,796 | 4 | 29 rows had no currency; defaulted to local currency |
| gl_opening_balance | 39 | 39 | 0 | - |

## Checks

| Entity | Check | Source | Target | Result |
|---|---|---|---|---|
| customer | row accounting (loaded + rejected) | 606 | 600 + 6 | ✅ |
| customer | key checksum (MD5) | db9df32af6be | db9df32af6be | ✅ |
| vendor | row accounting (loaded + rejected) | 150 | 150 + 0 | ✅ |
| vendor | key checksum (MD5) | 1676fa8c583e | 1676fa8c583e | ✅ |
| item | row accounting (loaded + rejected) | 400 | 400 + 0 | ✅ |
| item | key checksum (MD5) | 189294f40201 | 189294f40201 | ✅ |
| open_invoice | row accounting (loaded + rejected) | 1,800 | 1,796 + 4 | ✅ |
| open_invoice | key checksum (MD5) | 06a2c328c86c | 06a2c328c86c | ✅ |
| gl_opening_balance | row accounting (loaded + rejected) | 39 | 39 + 0 | ✅ |
| open_invoice | amount total AED (loaded + rejected) | 70,678,365.87 | 70,678,365.87 + 0.00 | ✅ |
| open_invoice | amount total LCY (loaded + rejected) | 220,319,651.49 | 220,049,115.44 + 270,536.05 | ✅ |
| open_invoice | amount total USD (loaded + rejected) | 61,480,730.78 | 61,480,730.78 + 0.00 | ✅ |
| gl_opening_balance | per-account totals match | 13 accounts | 13 match | ✅ |
| gl_opening_balance | trial balance nets to zero | 0.00 | 0.00 | ✅ |

## Rejects by reason (fix in source, then re-run)

| Entity | Reason | Rows |
|---|---|---:|
| customer | `duplicate_after_normalisation` | 6 |
| open_invoice | `orphan:Customer No.` | 4 |
