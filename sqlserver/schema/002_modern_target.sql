/* ATLAS normalized target schema. */
IF OBJECT_ID('dbo.customers', 'U') IS NULL
BEGIN
    CREATE TABLE dbo.customers (
        customer_id VARCHAR(32) NOT NULL CONSTRAINT pk_customers PRIMARY KEY,
        first_name NVARCHAR(100) NULL,
        last_name NVARCHAR(100) NULL,
        date_of_birth DATE NULL,
        status VARCHAR(16) NOT NULL,
        phone VARCHAR(64) NULL,
        country_code CHAR(2) NULL,
        created_at DATETIME2(3) NOT NULL CONSTRAINT df_customers_created DEFAULT SYSUTCDATETIME()
    );
END;
IF OBJECT_ID('dbo.accounts', 'U') IS NULL
BEGIN
    CREATE TABLE dbo.accounts (
        account_id VARCHAR(32) NOT NULL CONSTRAINT pk_accounts PRIMARY KEY,
        customer_id VARCHAR(32) NOT NULL,
        balance DECIMAL(20,4) NOT NULL,
        currency CHAR(3) NOT NULL,
        status VARCHAR(16) NOT NULL,
        opening_balance DECIMAL(20,4) NOT NULL,
        credits DECIMAL(20,4) NOT NULL,
        debits DECIMAL(20,4) NOT NULL,
        adjustments DECIMAL(20,4) NOT NULL,
        closing_balance DECIMAL(20,4) NOT NULL,
        CONSTRAINT fk_accounts_customer FOREIGN KEY (customer_id) REFERENCES dbo.customers(customer_id)
    );
END;
IF OBJECT_ID('dbo.transactions', 'U') IS NULL
BEGIN
    CREATE TABLE dbo.transactions (
        transaction_id VARCHAR(64) NOT NULL CONSTRAINT pk_transactions PRIMARY KEY,
        account_id VARCHAR(32) NOT NULL,
        amount DECIMAL(20,4) NOT NULL,
        currency CHAR(3) NOT NULL,
        type VARCHAR(32) NOT NULL,
        event_time DATETIME2(3) NULL,
        ingestion_time DATETIME2(3) NOT NULL CONSTRAINT df_transactions_ingestion DEFAULT SYSUTCDATETIME(),
        CONSTRAINT fk_transactions_account FOREIGN KEY (account_id) REFERENCES dbo.accounts(account_id)
    );
END;
GO
CREATE INDEX IF NOT EXISTS ix_accounts_customer ON dbo.accounts(customer_id);
CREATE INDEX IF NOT EXISTS ix_transactions_account_event ON dbo.transactions(account_id, event_time);
GO
