-- AX CUSTTRANSOPEN: the unsettled part of each customer transaction (open items / ageing).
CREATE OR ALTER VIEW ax.CUSTTRANSOPEN AS
SELECT
    t.ACCOUNTNUM,
    t.DATAAREAID,
    t.RECID                                   AS REFRECID,
    t.TRANSDATE,
    t.DUEDATE,
    t.CURRENCYCODE,
    ROUND(t.AMOUNTCUR - t.SETTLEAMOUNTCUR, 2) AS AMOUNTCUR
FROM ax.CUSTTRANS AS t
WHERE ROUND(t.AMOUNTCUR - t.SETTLEAMOUNTCUR, 2) <> 0;
