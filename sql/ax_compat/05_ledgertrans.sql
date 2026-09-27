-- AX LEDGERTRANS from BC G/L Entry (17). Every voucher is a balanced double entry.
CREATE OR ALTER VIEW ax.LEDGERTRANS AS
SELECT
    g.[GLAccountNo-3]                         AS ACCOUNTNUM,
    m.DATAAREAID                              AS DATAAREAID,
    CAST(g.[PostingDate-4] AS DATE)           AS TRANSDATE,
    g.[DocumentNo-6]                          AS VOUCHER,
    g.[Description-7]                         AS TXT,
    g.[Amount-17]                             AS AMOUNTMST,
    CASE WHEN g.[Amount-17] < 0 THEN 1 ELSE 0 END AS CREDITING,
    g.[EntryNo-1]                             AS RECID
FROM dbo.GLEntry_17 AS g
INNER JOIN dbo.company_map AS m
    ON m.CompanyName = g.[$Company];
