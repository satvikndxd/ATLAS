# SQL Server Concurrency Labs

These scripts are experiments, not production tuning advice. Run them against an isolated SQL Server test database with two sessions.

## Isolation experiment

```sql
-- Session A
SET TRANSACTION ISOLATION LEVEL READ COMMITTED;
BEGIN TRANSACTION;
SELECT * FROM dbo.accounts WHERE account_id = 'A000000100';
WAITFOR DELAY '00:00:05';
SELECT * FROM dbo.accounts WHERE account_id = 'A000000100';
COMMIT;

-- Session B during the delay
UPDATE dbo.accounts SET balance = balance + 1 WHERE account_id = 'A000000100';
COMMIT;
```

Repeat under `SNAPSHOT` and `SERIALIZABLE`. Record blocking, non-repeatable reads, and lock behavior in the benchmark artifact. ATLAS does not choose an isolation level globally; the adapter and workload must justify it.

## Deadlock pattern

```sql
-- Session A
BEGIN TRANSACTION;
UPDATE dbo.accounts SET balance = balance + 1 WHERE account_id = 'A000000100';
WAITFOR DELAY '00:00:03';
UPDATE dbo.customers SET status = 'ACTIVE' WHERE customer_id = 'C0000001';
COMMIT;

-- Session B
BEGIN TRANSACTION;
UPDATE dbo.customers SET status = 'ACTIVE' WHERE customer_id = 'C0000001';
WAITFOR DELAY '00:00:03';
UPDATE dbo.accounts SET balance = balance + 1 WHERE account_id = 'A000000100';
COMMIT;
```

The expected result is one victim transaction. The adapter should classify error 1205, record the deadlock evidence, retry only the idempotent unit of work with bounded backoff, and reconcile after retry. It must not claim that all retries are safe without an idempotency key.
