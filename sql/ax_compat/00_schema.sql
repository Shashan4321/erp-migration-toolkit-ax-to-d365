-- AX-compatible reporting layer on the Fabric lakehouse SQL analytics endpoint.
-- Tables (dbo.Customer_18, dbo.CustLedgerEntry_21, ...) are created by fabric/01_load_bc_export.ipynb.
-- Run the files in this folder in order: 00_schema, then 01..06 (one CREATE VIEW per batch).
IF NOT EXISTS (SELECT 1 FROM sys.schemas WHERE name = 'ax')
    EXEC ('CREATE SCHEMA ax');
