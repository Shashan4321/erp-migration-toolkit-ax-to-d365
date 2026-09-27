-- AX CUSTTABLE from BC Customer (table 18).
-- DATAAREAID comes from dbo.company_map, not a hard-coded CASE: adding a company is a data change,
-- and companies that are not mapped are reported by ax.DQ_UNMAPPED_COMPANIES instead of turning NULL.
CREATE OR ALTER VIEW ax.CUSTTABLE AS
SELECT
    c.[No-1]                          AS ACCOUNTNUM,
    c.[Name-2]                        AS NAME,
    c.[CustomerPostingGroup-21]       AS CUSTGROUP,
    COALESCE(NULLIF(c.[CurrencyCode-22], ''), 'INR') AS CURRENCY,
    c.[CountryRegionCode-35]          AS COUNTRYREGIONID,
    CASE c.[Blocked-39]
        WHEN 'Invoice' THEN 1
        WHEN 'All'     THEN 2
        ELSE 0
    END                               AS BLOCKED,
    m.DATAAREAID                      AS DATAAREAID
FROM dbo.Customer_18 AS c
INNER JOIN dbo.company_map AS m
    ON m.CompanyName = c.[$Company];
