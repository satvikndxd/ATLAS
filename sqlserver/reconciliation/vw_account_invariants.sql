CREATE OR ALTER VIEW dbo.vw_account_invariant_failures AS
SELECT
    account_id,
    opening_balance + credits - debits + adjustments AS expected_closing_balance,
    closing_balance,
    closing_balance - (opening_balance + credits - debits + adjustments) AS delta
FROM dbo.accounts
WHERE ABS(closing_balance - (opening_balance + credits - debits + adjustments)) > 0.0001;
GO

CREATE OR ALTER VIEW dbo.vw_reference_counts AS
SELECT 'customers' AS table_name, COUNT_BIG(*) AS row_count FROM dbo.customers
UNION ALL
SELECT 'accounts', COUNT_BIG(*) FROM dbo.accounts
UNION ALL
SELECT 'transactions', COUNT_BIG(*) FROM dbo.transactions;
GO
