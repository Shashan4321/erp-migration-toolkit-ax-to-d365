-- Data-quality view: BC companies with no row in dbo.company_map.
-- Their rows are excluded from the ax.* views, so this must be empty before reports are trusted.
CREATE OR ALTER VIEW ax.DQ_UNMAPPED_COMPANIES AS
SELECT
    src.SourceTable,
    src.CompanyName,
    COUNT(*) AS ROWS_EXCLUDED
FROM (
    SELECT 'Customer'               AS SourceTable, [$Company] AS CompanyName FROM dbo.Customer_18
    UNION ALL
    SELECT 'CustLedgerEntry'        AS SourceTable, [$Company] AS CompanyName FROM dbo.CustLedgerEntry_21
    UNION ALL
    SELECT 'BankAccountLedgerEntry' AS SourceTable, [$Company] AS CompanyName FROM dbo.BankAccountLedgerEntry_271
    UNION ALL
    SELECT 'GLEntry'                AS SourceTable, [$Company] AS CompanyName FROM dbo.GLEntry_17
) AS src
LEFT JOIN dbo.company_map AS m
    ON m.CompanyName = src.CompanyName
WHERE m.DATAAREAID IS NULL
GROUP BY src.SourceTable, src.CompanyName;
