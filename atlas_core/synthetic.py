"""Seeded synthetic banking data with controlled legacy defects."""
from __future__ import annotations

import random
from datetime import date, timedelta
from typing import Any


def _date(seed: random.Random, start: date, days: int = 3650) -> str:
    return (start + timedelta(days=seed.randrange(days))).isoformat()


def generate_legacy_bank(seed: int = 42, customers: int = 25, accounts_per_customer: int = 2, transactions_per_account: int = 6) -> dict[str, list[dict[str, Any]]]:
    rng = random.Random(seed)
    customer_rows: list[dict[str, Any]] = []
    account_rows: list[dict[str, Any]] = []
    transaction_rows: list[dict[str, Any]] = []
    beneficiary_rows: list[dict[str, Any]] = []
    risk_rows: list[dict[str, Any]] = []
    statuses = ["Y", "Yes", "1", "ACTIVE", "A", "N", "0", "CLOSED", "X"]
    currencies = ["USD", "EUR", "GBP", "INR"]
    for index in range(1, customers + 1):
        customer_no = f"C{index:07d}"
        full_name = f"Customer {index:04d}"
        if index % 11 == 0:
            full_name = f"  Customer {index:04d}  "
        dob = "31/02/1988" if index % 17 == 0 else _date(rng, date(1950, 1, 1), 18000)
        phone = "INVALID" if index % 13 == 0 else f"+1-555-{rng.randrange(1000000, 9999999)}"
        customer_rows.append({"customer_no": customer_no, "full_name": full_name, "dob": dob, "sex": rng.choice(["M", "F", "U"]), "status": rng.choice(statuses), "phone": phone, "country_code": rng.choice(["US", "GB", "IN", "DE"]), "updated_at": _date(rng, date(2020, 1, 1), 2200)})
        if index % 23 == 0:
            customer_rows.append(dict(customer_rows[-1]))
        for account_index in range(accounts_per_customer):
            account_no = f"A{index:07d}{account_index:02d}"
            opening = round(rng.uniform(100, 10000), 2)
            credits = round(rng.uniform(0, 2000), 2)
            debits = round(rng.uniform(0, 2000), 2)
            adjustments = round(rng.uniform(-10, 10), 2)
            closing = round(opening + credits - debits + adjustments, 2)
            account_rows.append({"acct_no": account_no, "customer_ref": customer_no, "acct_bal": str(closing), "currency": rng.choice(currencies), "status": rng.choice(statuses), "opening_balance": opening, "credits": credits, "debits": debits, "adjustments": adjustments, "closing_balance": closing})
            for transaction_index in range(transactions_per_account):
                transaction_id = f"T{index:07d}{account_index:02d}{transaction_index:03d}"
                amount = round(rng.uniform(1, 500), 2)
                if transaction_index == 0 and index % 19 == 0:
                    amount = -amount
                transaction_rows.append({"txn_id": transaction_id, "acct_ref": account_no, "amount": str(amount), "currency": account_rows[-1]["currency"], "txn_type": rng.choice(["CREDIT", "DEBIT", "REVERSAL", "CHARGEBACK"]), "event_date": _date(rng, date(2021, 1, 1), 1600), "ingest_date": _date(rng, date(2021, 1, 1), 1600)})
            beneficiary_rows.append({"beneficiary_id": f"B{index:07d}{account_index:02d}", "acct_ref": account_no, "name": f"Beneficiary {index}-{account_index}", "country_code": rng.choice(["US", "GB", "IN"])})
        if index % 7 == 0:
            risk_rows.append({"risk_id": f"R{index:07d}", "customer_ref": customer_no, "risk_code": rng.choice(["LOW", "MEDIUM", "HIGH"]), "event_date": _date(rng, date(2021, 1, 1), 1600)})
    if account_rows:
        transaction_rows.append({"txn_id": "T-ORPHAN", "acct_ref": "A-MISSING", "amount": "10.00", "currency": "USD", "txn_type": "DEBIT", "event_date": "2024-01-01", "ingest_date": "2024-01-01"})
    return {"legacy_customers": customer_rows, "legacy_accounts": account_rows, "legacy_transactions": transaction_rows, "legacy_beneficiaries": beneficiary_rows, "legacy_risk_events": risk_rows}


def normalize_status(value: Any) -> str:
    normalized = str(value).strip().upper()
    if normalized in {"Y", "YES", "1", "ACTIVE", "A"}:
        return "ACTIVE"
    if normalized in {"N", "NO", "0", "CLOSED", "X"}:
        return "CLOSED"
    return "UNKNOWN"


def modernize_bank(legacy: dict[str, list[dict[str, Any]]]) -> dict[str, list[dict[str, Any]]]:
    customers = [{"customer_id": row["customer_no"], "full_name": str(row["full_name"]).strip(), "date_of_birth": row["dob"], "status": normalize_status(row["status"]), "phone": row["phone"], "country_code": row["country_code"]} for row in legacy["legacy_customers"]]
    accounts = [{"account_id": row["acct_no"], "customer_id": row["customer_ref"], "balance": row["acct_bal"], "currency": row["currency"], "status": normalize_status(row["status"]), "opening_balance": row["opening_balance"], "credits": row["credits"], "debits": row["debits"], "adjustments": row["adjustments"], "closing_balance": row["closing_balance"]} for row in legacy["legacy_accounts"]]
    transactions = [{"transaction_id": row["txn_id"], "account_id": row["acct_ref"], "amount": row["amount"], "currency": row["currency"], "type": row["txn_type"], "event_time": row["event_date"], "ingestion_time": row["ingest_date"]} for row in legacy["legacy_transactions"]]
    beneficiaries = [{"beneficiary_id": row["beneficiary_id"], "account_id": row["acct_ref"], "name": row["name"], "country_code": row["country_code"]} for row in legacy["legacy_beneficiaries"]]
    risks = [{"risk_event_id": row["risk_id"], "customer_id": row["customer_ref"], "risk_code": row["risk_code"], "event_time": row["event_date"]} for row in legacy["legacy_risk_events"]]
    return {"customers": customers, "accounts": accounts, "transactions": transactions, "beneficiaries": beneficiaries, "risk_events": risks}
