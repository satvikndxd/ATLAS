# ATLAS Showcase Demo

The reference demo is intentionally small enough to run on a laptop while still exercising the difficult control paths.

```bash
python3 -m apps.cli.atlas_cli demo --seed 42 --customers 25 --batch-size 10
```

The command generates a seeded legacy banking dataset with inconsistent status values, malformed dates, duplicates, orphan transactions, and financial records. It executes resumable batches for customers, accounts, and transactions, writes checkpoints and hash-chained audit records, runs reconciliation, calculates risk, and prints JSON evidence.

To exercise the failure path:

```bash
python3 -m apps.cli.atlas_cli migrate golden-datasets/generated/legacy_accounts.json \
  --table legacy_accounts --key acct_no --fail-after 1 --batch-size 10 --state-dir .atlas/failure-demo
python3 -m apps.cli.atlas_cli migrate golden-datasets/generated/legacy_accounts.json \
  --table legacy_accounts --key acct_no --batch-size 10 --state-dir .atlas/failure-demo
```

The first command returns `PAUSED` after a committed checkpoint. The second resumes after the latest checkpoint and preserves idempotent target keys. This is a reference recovery demonstration, not a claim about distributed worker recovery under a live database cluster.
