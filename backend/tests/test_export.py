"""Tests for Excel and CSV export."""
from app.export.excel_exporter import export_excel
from app.export.csv_exporter import export_csv
from app.models import Statement


def test_excel_export():
    stmt = Statement(
        id="test-123",
        original_filename="sample.pdf",
        account_holder="Arjun Khanna",
        bank_name="HDFC Bank",
        account_number="1234567890",
        opening_balance=1000.0,
        closing_balance=1500.0,
    )
    txns = [
        {
            "date": "2025-06-01",
            "description": "Salary",
            "original_description": "SALARY CREDIT",
            "debit": None,
            "credit": 500.0,
            "balance": 1500.0,
            "category": "Salary & Income",
            "classification_method": "rule_based",
            "confidence": 0.98,
            "review_status": "pending",
            "validation_flags": [],
            "source_page": 1,
        }
    ]
    excel_bytes = export_excel(stmt, txns, {"reconciled": True, "flagged_count": 0})
    assert len(excel_bytes) > 1000
    assert excel_bytes[:4] == b"PK\x03\x04"  # zip header for xlsx


def test_csv_export():
    txns = [
        {
            "date": "2025-06-01",
            "description": "Swiggy Order",
            "original_description": "UPI/SWIGGY/ORDER",
            "debit": 350.0,
            "credit": None,
            "balance": 1150.0,
            "category": "Food & Dining",
            "classification_method": "rule_based",
            "confidence": 0.95,
            "review_status": "pending",
            "validation_flags": [],
            "source_page": 1,
        }
    ]
    csv_bytes = export_csv(txns)
    csv_str = csv_bytes.decode("utf-8-sig")
    assert "date,description" in csv_str
    assert "Swiggy Order" in csv_str
    assert "350.0" in csv_str

