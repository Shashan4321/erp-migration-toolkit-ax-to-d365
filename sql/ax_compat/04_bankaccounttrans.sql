-- AX BANKACCOUNTTRANS from BC Bank Account Ledger Entry (271).
CREATE OR ALTER VIEW ax.BANKACCOUNTTRANS AS
SELECT
    b.[BankAccountNo-3]                       AS ACCOUNTID,
    m.DATAAREAID                              AS DATAAREAID,
    CAST(b.[PostingDate-4] AS DATE)           AS TRANSDATE,
    b.[DocumentNo-6]                          AS VOUCHER,
    b.[Description-7]                         AS TXT,
    COALESCE(NULLIF(b.[CurrencyCode-11], ''), 'INR') AS CURRENCYCODE,
    b.[Amount-13]                             AS AMOUNTCUR,
    CASE WHEN b.[Open-36] = 1 THEN 0 ELSE 1 END AS RECONCILED,
    b.[EntryNo-1]                             AS RECID
FROM dbo.BankAccountLedgerEntry_271 AS b
INNER JOIN dbo.company_map AS m
    ON m.CompanyName = b.[$Company];
