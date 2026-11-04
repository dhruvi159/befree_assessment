"""Tests for API routes."""
import pytest
from app.database import SessionLocal, init_db
from app.routers.health import health_check
from app.routers.dashboard import get_dashboard
from app.routers.rules import get_rules, create_rule, delete_rule
from app.routers.model import get_model_metrics
from app.routers.statements import purge_all_data
from app.schemas import RuleCreate


@pytest.fixture(scope="module")
def db():
    init_db()
    session = SessionLocal()
    try:
        yield session
    finally:
        session.close()


def test_health_endpoint():
    res = health_check()
    assert res.status == "healthy"
    assert res.database_connected is True
    assert hasattr(res, "ml_model_loaded")


def test_dashboard_empty_or_data(db):
    res = get_dashboard(db=db)
    assert hasattr(res, "has_data")


def test_rules_crud(db):
    # List initial rules
    initial = get_rules(db=db)
    initial_count = initial.total

    # Create new rule
    new_rule = RuleCreate(
        category="Food & Dining",
        rule_type="keyword",
        pattern="testcafekeyword",
        priority=99,
        is_active=True,
    )
    created = create_rule(rule_in=new_rule, db=db)
    assert created.id is not None
    assert created.pattern == "testcafekeyword"

    # Verify count increased
    after_create = get_rules(db=db)
    assert after_create.total == initial_count + 1

    # Delete rule
    delete_rule(rule_id=created.id, db=db)
    after_delete = get_rules(db=db)
    assert after_delete.total == initial_count


def test_model_metrics(db):
    metrics = get_model_metrics(db=db)
    assert metrics.version is not None
    assert hasattr(metrics, "is_active")


def test_purge_endpoint(db):
    res = purge_all_data(db=db)
    assert "purged" in res["message"].lower()
