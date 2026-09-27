-- AX CUSTTRANS from BC Cust. Ledger Entry (21) + Detailed Cust. Ledg. Entry (379).
-- In BC the amounts are FlowFields over the detailed entries, so they are summed here:
--   AMOUNTCUR       = the 'Initial Entry' amount (the transaction itself)
--   SETTLEAMOUNTCUR = how much of it has been settled by applications (same sign as AMOUNTCUR)
CREATE OR ALTER VIEW ax.CUSTTRANS AS
WITH amounts AS (
    SELECT
        d.[CustLedgerEntryNo-2]  AS CleNo,
        d.[$Company]             AS Company,
        SUM(CASE WHEN d.[EntryType-3] = 'Initial Entry' THEN d.[Amount-7] ELSE 0 END) AS AmountCur,
        SUM(CASE WHEN d.[EntryType-3] = 'Application'   THEN d.[Amount-7] ELSE 0 END) AS AppliedCur
    FROM dbo.DetailedCustLedgEntry_379 AS d
    GROUP BY d.[CustLedgerEntryNo-2], d.[$Company]
)
SELECT
    cl.[CustomerNo-3]                        AS ACCOUNTNUM,
    cl.[CustomerName-8]                      AS NAME,
    cl.[CustomerPostingGroup-22]             AS CUSTGROUP,
    m.DATAAREAID                             AS DATAAREAID,
    CAST(cl.[PostingDate-4] AS DATE)         AS TRANSDATE,
    cl.[DocumentNo-6]                        AS VOUCHER,
    CASE WHEN cl.[DocumentType-5] = 'Invoice' THEN cl.[DocumentNo-6] END AS INVOICE,
    cl.[Description-7]                       AS TXT,
    UPPER(cl.[DocumentType-5])               AS TRANSTYPE,
    COALESCE(NULLIF(cl.[CurrencyCode-11], ''), 'INR') AS CURRENCYCODE,
    COALESCE(a.AmountCur, 0)                 AS AMOUNTCUR,
    -COALESCE(a.AppliedCur, 0)               AS SETTLEAMOUNTCUR,
    cl.[GlobalDimension1Code-23]             AS DIMENSION,     -- branch
    cl.[GlobalDimension2Code-24]             AS DIMENSION2_,   -- department
    CAST(cl.[DueDate-37] AS DATE)            AS DUEDATE,
    CAST(cl.[DocumentDate-62] AS DATE)       AS DOCUMENTDATE,
    cl.[EntryNo-1]                           AS RECID
FROM dbo.CustLedgerEntry_21 AS cl
INNER JOIN dbo.company_map AS m
    ON m.CompanyName = cl.[$Company]
LEFT JOIN amounts AS a
    ON a.CleNo = cl.[EntryNo-1]
   AND a.Company = cl.[$Company];
