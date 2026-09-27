# Source data profiling (synthetic AX extract)

## Issues found

- CUSTTABLE.ACCOUNTNUM: 6 with leading/trailing spaces
- CUSTTABLE.CUSTGROUP: 9 with leading/trailing spaces
- CUSTTABLE.CUSTGROUP: mixed case codes
- CUSTTABLE.CURRENCY: 8 missing values
- CUSTTABLE.EMAIL: 8 invalid e-mails
- CUSTTABLE.CITY: 2 with leading/trailing spaces
- CUSTTABLE.ACCOUNTNUM: 6 duplicate keys after trim/upper
- CUSTTRANSOPEN.CURRENCYCODE: 29 missing values
- INVENTTABLE.UNITID: 5 missing values

## CUSTTABLE (606 rows)

| column     |   null_pct |   distinct | sample               | flags                                            |
|:-----------|-----------:|-----------:|:---------------------|:-------------------------------------------------|
| ACCOUNTNUM |        0   |        606 | C00001               | 6 with leading/trailing spaces                   |
| NAME       |        0   |        594 | Dora-Rana            |                                                  |
| CUSTGROUP  |        0   |          8 | RETAIL               | 9 with leading/trailing spaces; mixed case codes |
| CURRENCY   |        1.3 |          3 | USD                  |                                                  |
| EMAIL      |        0   |        593 | butalaurmi@doshi.com | 8 invalid e-mails                                |
| CITY       |        0   |        273 | Madurai              | 2 with leading/trailing spaces                   |
| CREDITMAX  |        0   |          5 | 250000.0             |                                                  |
| BLOCKED    |        0   |          3 | 2                    |                                                  |
| DATAAREAID |        0   |          1 | demo                 |                                                  |

## CUSTTRANSOPEN (1,800 rows)

| column       |   null_pct |   distinct | sample     | flags   |
|:-------------|-----------:|-----------:|:-----------|:--------|
| RECID        |        0   |       1800 | 5000001    |         |
| ACCOUNTNUM   |        0   |        571 | C00247     |         |
| INVOICE      |        0   |       1800 | INV-000001 |         |
| TRANSDATE    |        0   |        359 | 2024-09-28 |         |
| DUEDATE      |      100   |          0 |            |         |
| AMOUNTCUR    |        0   |       1800 | 360639.01  |         |
| CURRENCYCODE |        1.6 |          3 | USD        |         |
| DATAAREAID   |        0   |          1 | demo       |         |

## INVENTTABLE (400 rows)

| column      |   null_pct |   distinct | sample        | flags   |
|:------------|-----------:|-----------:|:--------------|:--------|
| ITEMID      |        0   |        400 | IT-00001      |         |
| ITEMNAME    |        0   |        399 | Repellat quos |         |
| ITEMGROUPID |        0   |          4 | SPARE         |         |
| UNITID      |        1.2 |          4 | BOX           |         |
| PRICE       |        0   |        400 | 9619.15       |         |
| DATAAREAID  |        0   |          1 | demo          |         |

## LEDGERBALANCE (39 rows)

| column      |   null_pct |   distinct | sample       | flags   |
|:------------|-----------:|-----------:|:-------------|:--------|
| ACCOUNTNUM  |          0 |         13 | 110100       |         |
| ACCOUNTNAME |          0 |         13 | Cash at bank |         |
| DEPARTMENT  |          0 |          3 | SALES        |         |
| AMOUNTMST   |          0 |         39 | 5529359.25   |         |
| DATAAREAID  |          0 |          1 | demo         |         |

## VENDTABLE (150 rows)

| column     |   null_pct |   distinct | sample              | flags   |
|:-----------|-----------:|-----------:|:--------------------|:--------|
| ACCOUNTNUM |          0 |        150 | V00001              |         |
| NAME       |          0 |        150 | Khatri-Venkataraman |         |
| VENDGROUP  |          0 |          3 | IMPORT              |         |
| CURRENCY   |          0 |          3 | AED                 |         |
| PAYMTERMID |          0 |          4 | COD                 |         |
| DATAAREAID |          0 |          1 | demo                |         |
