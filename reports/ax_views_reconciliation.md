# AX-compatible views: reconciliation

Output of `python -m erpmig.ax_views`: the T-SQL views in `sql/ax_compat/` run on the synthetic
BC export and are compared with the source tables, per company (DATAAREAID).

**10/10 checks pass.**

| check                                                         | ax_view                                 | bc_source                               | passed   |
|:--------------------------------------------------------------|:----------------------------------------|:----------------------------------------|:---------|
| company_map has one row per company                           | 0                                       | 0                                       | ✅        |
| CUSTTABLE rows = mapped Customer rows                         | {'cgl': 180, 'cin': 180}                | {'cgl': 180, 'cin': 180}                | ✅        |
| CUSTTRANS rows = mapped Cust. Ledger Entry rows               | {'cgl': 2713, 'cin': 2695}              | {'cgl': 2713, 'cin': 2695}              | ✅        |
| CUSTTRANS AMOUNTCUR = detailed 'Initial Entry' amounts        | {'cgl': 9285604.55, 'cin': 10210909.14} | {'cgl': 9285604.55, 'cin': 10210909.14} | ✅        |
| CUSTTRANSOPEN balance = sum of all detailed entries (open AR) | {'cgl': 9285604.55, 'cin': 10210909.14} | {'cgl': 9285604.55, 'cin': 10210909.14} | ✅        |
| CUSTTRANSOPEN items = BC entries flagged Open                 | {'cgl': 287, 'cin': 305}                | {'cgl': 287, 'cin': 305}                | ✅        |
| BANKACCOUNTTRANS amount = Bank Account Ledger Entry amount    | {'cgl': 42261246.1, 'cin': 40751561.61} | {'cgl': 42261246.1, 'cin': 40751561.61} | ✅        |
| LEDGERTRANS nets to zero per company (double entry)           | {'cgl': 0, 'cin': 0}                    | {'cgl': 0.0, 'cin': 0.0}                | ✅        |
| No NULL DATAAREAID in any ax.* view                           | 0                                       | 0                                       | ✅        |
| DQ view reports the unmapped sandbox company                  | ['CRONUS Test Sandbox']                 | ['CRONUS Test Sandbox']                 | ✅        |

## View row counts

| view             |   rows |
|:-----------------|-------:|
| CUSTTABLE        |    360 |
| CUSTTRANS        |   5408 |
| CUSTTRANSOPEN    |    592 |
| BANKACCOUNTTRANS |   2408 |
| LEDGERTRANS      |  10816 |

## ax.DQ_UNMAPPED_COMPANIES

| SourceTable            | CompanyName         |   ROWS_EXCLUDED |
|:-----------------------|:--------------------|----------------:|
| BankAccountLedgerEntry | CRONUS Test Sandbox |              16 |
| CustLedgerEntry        | CRONUS Test Sandbox |              36 |
| Customer               | CRONUS Test Sandbox |               5 |
| GLEntry                | CRONUS Test Sandbox |              72 |
