/* Safe, parameterized upsert pattern. MERGE is intentionally avoided because
   explicit update/insert paths make affected-row reasoning and retry behavior clearer. */
CREATE OR ALTER PROCEDURE dbo.usp_upsert_account
    @account_id VARCHAR(32),
    @customer_id VARCHAR(32),
    @balance DECIMAL(20,4),
    @currency CHAR(3),
    @status VARCHAR(16),
    @opening_balance DECIMAL(20,4),
    @credits DECIMAL(20,4),
    @debits DECIMAL(20,4),
    @adjustments DECIMAL(20,4),
    @closing_balance DECIMAL(20,4)
AS
BEGIN
    SET NOCOUNT ON;
    SET XACT_ABORT ON;
    SET TRANSACTION ISOLATION LEVEL SNAPSHOT;
    BEGIN TRY
        BEGIN TRANSACTION;
        IF EXISTS (SELECT 1 FROM dbo.accounts WITH (UPDLOCK, HOLDLOCK) WHERE account_id = @account_id)
        BEGIN
            UPDATE dbo.accounts
            SET customer_id = @customer_id, balance = @balance, currency = @currency,
                status = @status, opening_balance = @opening_balance, credits = @credits,
                debits = @debits, adjustments = @adjustments, closing_balance = @closing_balance
            WHERE account_id = @account_id;
        END
        ELSE
        BEGIN
            INSERT INTO dbo.accounts(account_id, customer_id, balance, currency, status, opening_balance, credits, debits, adjustments, closing_balance)
            VALUES (@account_id, @customer_id, @balance, @currency, @status, @opening_balance, @credits, @debits, @adjustments, @closing_balance);
        END;
        COMMIT TRANSACTION;
    END TRY
    BEGIN CATCH
        IF XACT_STATE() <> 0 ROLLBACK TRANSACTION;
        THROW;
    END CATCH;
END;
GO
