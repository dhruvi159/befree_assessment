"""Dashboard aggregation endpoint."""
import logging
from collections import defaultdict
from datetime import datetime
from typing import Optional

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.database import get_db
from app.models import Statement, Transaction
from app.schemas import DashboardResponse, KPIData, CategoryBreakdown, MonthlyTrend, StatementResponse, TransactionResponse
from app.utils.masking import mask_account_display

logger = logging.getLogger(__name__)
router = APIRouter()


@router.get("/dashboard", response_model=DashboardResponse)
def get_dashboard(db: Session = Depends(get_db)):
    """
    Aggregate dashboard data across all completed statements.
    Returns empty state if no data exists.
    """
    statements = (
        db.query(Statement)
        .filter(Statement.status == "completed")
        .order_by(Statement.created_at.desc())
        .all()
    )

    if not statements:
        return DashboardResponse(has_data=False)

    # Gather all transactions from all completed statements
    all_transactions = (
        db.query(Transaction)
        .filter(Transaction.statement_id.in_([s.id for s in statements]))
        .order_by(Transaction.date.desc())
        .all()
    )

    if not all_transactions:
        return DashboardResponse(has_data=False)

    # ── KPIs ────────────────────────────────────────────────────
    total_credits = sum(t.credit or 0 for t in all_transactions)
    total_debits = sum(t.debit or 0 for t in all_transactions)
    uncategorized = sum(1 for t in all_transactions if t.category == "Uncategorized")
    needing_review = sum(1 for t in all_transactions if t.review_status == "review_required")

    kpis = KPIData(
        total_transactions=len(all_transactions),
        total_credits=round(total_credits, 2),
        total_debits=round(total_debits, 2),
        uncategorized=uncategorized,
        needing_review=needing_review,
        net_change=round(total_credits - total_debits, 2),
    )

    # ── Spending by category ────────────────────────────────────
    cat_totals: dict[str, dict] = defaultdict(lambda: {"total": 0.0, "count": 0})
    for t in all_transactions:
        if t.debit and t.debit > 0:
            cat_totals[t.category or "Uncategorized"]["total"] += t.debit
            cat_totals[t.category or "Uncategorized"]["count"] += 1

    total_spend = sum(v["total"] for v in cat_totals.values()) or 1
    spending_by_category = [
        CategoryBreakdown(
            category=cat,
            total=round(data["total"], 2),
            count=data["count"],
            percentage=round(data["total"] / total_spend * 100, 1),
        )
        for cat, data in sorted(cat_totals.items(), key=lambda x: x[1]["total"], reverse=True)
    ]

    # ── Monthly trends ──────────────────────────────────────────
    monthly: dict[str, dict] = defaultdict(lambda: {"credits": 0.0, "debits": 0.0})
    for t in all_transactions:
        if t.date:
            try:
                month_key = t.date[:7]  # YYYY-MM
                monthly[month_key]["credits"] += t.credit or 0
                monthly[month_key]["debits"] += t.debit or 0
            except Exception:
                pass

    monthly_trends = [
        MonthlyTrend(
            month=month,
            credits=round(data["credits"], 2),
            debits=round(data["debits"], 2),
        )
        for month, data in sorted(monthly.items())
    ]

    # ── Recent transactions ─────────────────────────────────────
    recent = all_transactions[:10]
    recent_txns = [_txn_to_response(t) for t in recent]

    # ── Statements list ─────────────────────────────────────────
    stmt_responses = [_stmt_to_response(s) for s in statements[:5]]

    # ── Account info (from most recent statement) ───────────────
    latest = statements[0]
    account_info = {
        "account_holder": latest.account_holder,
        "bank_name": latest.bank_name,
        "account_number_masked": mask_account_display(latest.account_number),
        "ifsc_code": latest.ifsc_code,
        "branch": latest.branch,
        "statement_period_start": latest.statement_period_start,
        "statement_period_end": latest.statement_period_end,
        "opening_balance": latest.opening_balance,
        "closing_balance": latest.closing_balance,
    }

    return DashboardResponse(
        has_data=True,
        kpis=kpis,
        spending_by_category=spending_by_category,
        monthly_trends=monthly_trends,
        recent_transactions=recent_txns,
        statements=stmt_responses,
        account_info=account_info,
    )


def _txn_to_response(t: Transaction) -> TransactionResponse:
    return TransactionResponse(
        id=t.id,
        statement_id=t.statement_id,
        date=t.date,
        description=t.description,
        original_description=t.original_description,
        debit=t.debit,
        credit=t.credit,
        balance=t.balance,
        source_page=t.source_page,
        category=t.category or "Uncategorized",
        classification_method=t.classification_method or "unclassified",
        confidence=t.confidence,
        review_status=t.review_status or "pending",
        validation_flags=t.validation_flags or [],
        ocr_confidence=t.ocr_confidence,
        created_at=t.created_at,
        updated_at=t.updated_at,
    )


def _stmt_to_response(s: Statement) -> StatementResponse:
    return StatementResponse(
        id=s.id,
        original_filename=s.original_filename,
        file_size=s.file_size,
        page_count=s.page_count,
        pdf_type=s.pdf_type,
        status=s.status,
        processing_progress=s.processing_progress or 0,
        processing_message=s.processing_message or "",
        error_message=s.error_message,
        account_holder=s.account_holder,
        bank_name=s.bank_name,
        account_number_masked=mask_account_display(s.account_number),
        ifsc_code=s.ifsc_code,
        branch=s.branch,
        statement_period_start=s.statement_period_start,
        statement_period_end=s.statement_period_end,
        opening_balance=s.opening_balance,
        closing_balance=s.closing_balance,
        created_at=s.created_at,
        completed_at=s.completed_at,
    )

