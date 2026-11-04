"""Tests for financial balance reconciliation and data validator."""
from app.validation.balance_checker import check_balance_reconciliation
from app.validation.data_validator import validate_transactions


def test_balance_reconciliation_exact():
    # Opening 1000
    txns = [
        {"date": "2025-06-01", "debit": None, "credit": 500.0, "balance": 1500.0},
        {"date": "2025-06-02", "debit": 200.0, "credit": None, "balance": 1300.0},
        {"date": "2025-06-03", "debit": 300.0, "credit": None, "balance": 1000.0},
    ]
    res = check_balance_reconciliation(txns, opening_balance=1000.0)
    assert res["reconciled"] is True
    assert res["discrepancy"] is None
    assert len(res["flagged_indices"]) == 0


def test_balance_reconciliation_discrepancy():
    # Opening 1000, row 2 has incorrect balance 1400 instead of 1300
    txns = [
        {"date": "2025-06-01", "debit": None, "credit": 500.0, "balance": 1500.0},
        {"date": "2025-06-02", "debit": 200.0, "credit": None, "balance": 1400.0}, # error
    ]
    res = check_balance_reconciliation(txns, opening_balance=1000.0)
    assert res["reconciled"] is False
    assert res["discrepancy"] == 100.0
    assert 1 in res["flagged_indices"]


def test_data_validator_flags():
    txns = [
        {"date": None, "description": "No date", "debit": 100.0, "balance": 900.0},
        {"date": "2025-06-01", "description": "No amount", "debit": None, "credit": None, "balance": 900.0},
        {"date": "2025-06-02", "description": "Both populated", "debit": 100.0, "credit": 50.0, "balance": 850.0},
    ]
    validated, summary = validate_transactions(txns, opening_balance=1000.0)
    assert summary["flagged_count"] == 3
    assert "missing_date" in validated[0]["validation_flags"]
    assert "missing_amount" in validated[1]["validation_flags"]
    assert "both_debit_and_credit" in validated[2]["validation_flags"]

