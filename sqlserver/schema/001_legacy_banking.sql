/* ATLAS legacy banking reference schema.
   Deliberately preserves inconsistent legacy representations for migration tests. */
IF OBJECT_ID('dbo.legacy_customers', 'U') IS NULL
BEGIN
    CREATE TABLE dbo.legacy_customers (
        customer_no VARCHAR(32) NOT NULL PRIMARY KEY,
        full_name VARCHAR(200) NULL,
        dob VARCHAR(10) NULL,
        sex CHAR(1) NULL,
        status CHAR(12) NULL,
        phone VARCHAR(64) NULL,
        country_code CHAR(2) NULL,
        updated_at DATETIME2(3) NULL
    );
END;
IF OBJECT_ID('dbo.legacy_accounts', 'U') IS NULL
BEGIN
    CREATE TABLE dbo.legacy_accounts (
        acct_no VARCHAR(32) NOT NULL PRIMARY KEY,
        customer_ref VARCHAR(32) NULL,
        acct_bal VARCHAR(64) NULL,
        currency VARCHAR(8) NULL,
        status CHAR(12) NULL,
        opening_balance DECIMAL(20,4) NULL,
        credits DECIMAL(20,4) NULL,
        debits DECIMAL(20,4) NULL,
        adjustments DECIMAL(20,4) NULL,
        closing_balance DECIMAL(20,4) NULL
    );
END;
IF OBJECT_ID('dbo.legacy_transactions', 'U') IS NULL
BEGIN
    CREATE TABLE dbo.legacy_transactions (
        txn_id VARCHAR(64) NOT NULL PRIMARY KEY,
        acct_ref VARCHAR(32) NULL,
        amount VARCHAR(64) NULL,
        currency VARCHAR(8) NULL,
        txn_type VARCHAR(32) NULL,
        event_date VARCHAR(32) NULL,
        ingest_date VARCHAR(32) NULL
    );
END;
GO
