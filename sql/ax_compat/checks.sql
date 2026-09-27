-- Run after 00..06 in the SQL analytics endpoint. Compare with reports/ax_views_reconciliation.md.

-- 1. Must be exactly one row: 'CRONUS Test Sandbox' (deliberately unmapped). Anything else = fix company_map.
SELECT * FROM ax.DQ_UNMAPPED_COMPANIES ORDER BY SourceTable;

-- 2. Open receivables per company: must equal the sum of all detailed entries per company.
SELECT o.DATAAREAID, COUNT(*) AS open_items, SUM(o.AMOUNTCUR) AS open_amount
FROM ax.CUSTTRANSOPEN AS o
GROUP BY o.DATAAREAID
ORDER BY o.DATAAREAID;

-- 3. Ledger nets to zero per company (double entry).
SELECT DATAAREAID, SUM(AMOUNTMST) AS net
FROM ax.LEDGERTRANS
GROUP BY DATAAREAID;

-- 4. A typical legacy AX report query, unchanged after the migration: overdue receivables by branch.
SELECT t.DATAAREAID, t.DIMENSION AS BRANCH, c.CUSTGROUP,
       COUNT(*) AS overdue_items, SUM(o.AMOUNTCUR) AS overdue_amount
FROM ax.CUSTTRANSOPEN AS o
JOIN ax.CUSTTRANS AS t ON t.RECID = o.REFRECID AND t.DATAAREAID = o.DATAAREAID
JOIN ax.CUSTTABLE AS c ON c.ACCOUNTNUM = o.ACCOUNTNUM AND c.DATAAREAID = o.DATAAREAID
WHERE o.DUEDATE < '2026-09-15'
GROUP BY t.DATAAREAID, t.DIMENSION, c.CUSTGROUP
ORDER BY overdue_amount DESC;
