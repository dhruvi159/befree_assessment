"""Tests for classification engine: rules + ML."""
import pytest
from app.classification.preprocessor import normalize_narration, extract_merchant
from app.classification.rule_engine import apply_rules
from app.classification.ml_classifier import predict, is_model_available, reload_model
from app.classification.classifier import classify_transaction
from app.database import SessionLocal, init_db
from app.models import Transaction, Statement
from ml.train import train_on_real_data


@pytest.fixture(scope="module", autouse=True)
def trained_real_model():
    """Seed real statement transactions and train model on real statement data."""
    init_db()
    db = SessionLocal()
    # Insert real statement transactions
    sample_txns = [
        ("SWIGGY BANGALORE IN", "Food & Dining"),
        ("ZOMATO RESTAURANT GURGAON", "Food & Dining"),
        ("MCDONALDS CONNAUGHT PLACE", "Food & Dining"),
        ("STARBUCKS COFFEE MUMBAI", "Food & Dining"),
        ("UBER RIDE TRIPS MUMBAI", "Transportation"),
        ("OLA CABS BANGALORE", "Transportation"),
        ("METRO RECHARGE DELHI", "Transportation"),
        ("SHELL PETROL PUMP BANGALORE", "Transportation"),
        ("SALARY CREDITED INFOSYS TECH", "Salary & Income"),
        ("SALARY MONTHLY CREDIT TCS LTD", "Salary & Income"),
        ("PAYROLL DIRECT DEPOSIT WIPRO", "Salary & Income"),
    ]
    created = []
    for desc, cat in sample_txns:
        t = Transaction(statement_id="test_stmt", description=desc, original_description=desc, category=cat)
        db.add(t)
        created.append(t)
    db.commit()

    train_on_real_data(db_session=db)
    yield
    for t in created:
        db.delete(t)
    db.commit()
    db.close()


def test_normalize_narration():
    raw = "UPI/SWIGGY/421745903870/ORDER FOOD @okhdfcbank"
    clean = normalize_narration(raw)
    assert "swiggy" in clean
    assert "@" not in clean
    assert "421745903870" not in clean


def test_extract_merchant():
    merchant = extract_merchant("UPI/SWIGGY/421745903870/ORDER FOOD")
    assert "swiggy" in merchant.lower()


def test_rule_based_food():
    res = apply_rules("UPI/ZOMATO/ORDER 4218")
    assert res is not None
    assert res["category"] == "Food & Dining"
    assert res["classification_method"] == "rule_based"


def test_rule_based_transport():
    res = apply_rules("UPI/UBER INDIA/421609153882")
    assert res is not None
    assert res["category"] == "Transportation"


def test_rule_based_salary():
    res = apply_rules("SALARY CREDIT JUNE 2025 INFOSYS")
    assert res is not None
    assert res["category"] == "Salary & Income"


def test_ml_prediction():
    assert is_model_available()
    pred = predict("SWIGGY BANGALORE IN")
    assert pred is not None
    assert pred["category"] == "Food & Dining"
    assert pred["classification_method"] == "machine_learning"
    assert 0.0 <= pred["confidence"] <= 1.0


def test_combined_decision_flow():
    # Rule match
    r1 = classify_transaction("UPI/DOMINOS PIZZA")
    assert r1["category"] == "Food & Dining"
    assert r1["classification_method"] == "rule_based"

    # ML fallback
    r2 = classify_transaction("NETFLIX ENTERTAINMENT SERVICES")
    assert r2["category"] == "Entertainment"

    # Obscure unknown narration -> unclassified / review required
    r3 = classify_transaction("XYZBLAHBLAHBLAH999")
    assert r3["review_status"] == "review_required"

