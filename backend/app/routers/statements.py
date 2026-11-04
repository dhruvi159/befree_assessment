"""Statement upload and management endpoints."""
import logging
import os
import uuid
from collections import defaultdict
from datetime import datetime
from typing import Optional

from fastapi import (
    APIRouter, BackgroundTasks, Depends, File, Form,
    HTTPException, Query, UploadFile
)
from fastapi.responses import StreamingResponse, Response
from sqlalchemy.orm import Session

from app.database import get_db
from app.models import Statement, Transaction, Correction
from app.schemas import (
    StatementResponse, StatementStatusResponse,
    TransactionListResponse, TransactionResponse, TransactionUpdate,
    ValidationSummary, ValidationFlag, AnalyticsResponse,
    CategoryBreakdown, MonthlyTrend
)
from app.config import settings
from app.utils.masking import mask_account_display

logger = logging.getLogger(__name__)
router = APIRouter()


# â”€â”€ Upload â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€

@router.post("/statements/upload", response_model=StatementResponse, status_code=202)
async def upload_statement(
    background_tasks: BackgroundTasks,
    file: UploadFile = File(...),
    password: Optional[str] = Form(None),
    db: Session = Depends(get_db),
):
    """
    Upload a bank statement PDF and start background processing.
    """
    # Validate file type
    if not file.filename or not file.filename.lower().endswith(".pdf"):
        raise HTTPException(status_code=400, detail="Only PDF files are accepted.")

    # Validate file size
    contents = await file.read()
    if len(contents) > settings.max_upload_bytes:
        raise HTTPException(
            status_code=413,
            detail=f"File exceeds {settings.max_upload_mb} MB limit."
        )

    # Save with UUID filename for privacy
    safe_filename = f"{uuid.uuid4()}.pdf"
    upload_path = settings.upload_dir / safe_filename
    with open(upload_path, "wb") as f:
        f.write(contents)

    # Create statement record
    statement = Statement(
        id=str(uuid.uuid4()),
        original_filename=file.filename,
        stored_filename=safe_filename,
        file_size=len(contents),
        status="uploaded",
        processing_progress=0.0,
        processing_message="Queued for processing",
    )
    db.add(statement)
    db.commit()
    db.refresh(statement)

    # Start background processing
    from app.pipeline.orchestrator import process_statement
    from app.database import SessionLocal

    def run_pipeline():
        """Run pipeline in a new DB session (background task)."""
        bg_db = SessionLocal()
        try:
            process_statement(
                statement_id=statement.id,
                pdf_path=str(upload_path),
                password=password,
                db_session=bg_db,
            )
        finally:
            bg_db.close()

    background_tasks.add_task(run_pipeline)

    return _stmt_to_response(statement)


# â”€â”€ List & Get â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€

@router.get("/statements", response_model=list[StatementResponse])
def list_statements(db: Session = Depends(get_db)):
    """List all statements, newest first."""
    statements = db.query(Statement).order_by(Statement.created_at.desc()).all()
    return [_stmt_to_response(s) for s in statements]


@router.get("/statements/{statement_id}", response_model=StatementResponse)
def get_statement(statement_id: str, db: Session = Depends(get_db)):
    """Get a single statement by ID."""
    stmt = db.query(Statement).filter(Statement.id == statement_id).first()
    if not stmt:
        raise HTTPException(status_code=404, detail="Statement not found")
    return _stmt_to_response(stmt)


@router.get("/statements/{statement_id}/status", response_model=StatementStatusResponse)
def get_statement_status(statement_id: str, db: Session = Depends(get_db)):
    """Poll processing status for a statement."""
    stmt = db.query(Statement).filter(Statement.id == statement_id).first()
    if not stmt:
        raise HTTPException(status_code=404, detail="Statement not found")

    page_types = None
    if stmt.page_types:
        from app.schemas import PageTypeInfo
        page_types = [PageTypeInfo(**p) for p in stmt.page_types]

    return StatementStatusResponse(
        id=stmt.id,
        status=stmt.status,
        processing_progress=stmt.processing_progress or 0,
        processing_message=stmt.processing_message or "",
        error_message=stmt.error_message,
        pdf_type=stmt.pdf_type,
        page_types=page_types,
        page_count=stmt.page_count,
    )


# â”€â”€ Transactions â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€

@router.post("/statements/purge")
def purge_all_data(db: Session = Depends(get_db)):
    """
    Purge all statements, transactions, and corrections from the database.
    Clean up any leftover files in the upload directory.
    """
    db.query(Transaction).delete()
    db.query(Correction).delete()
    db.query(Statement).delete()
    db.commit()

    # Clean up any leftover upload binaries
    try:
        if settings.upload_dir.exists():
            for f in settings.upload_dir.glob("*.pdf"):
                try:
                    f.unlink()
                except Exception:
                    pass
    except Exception as e:
        logger.warning(f"Error cleaning upload dir: {e}")

    return {"message": "All statement data, transactions, and temporary files have been permanently purged."}


@router.delete("/statements/{statement_id}")
def delete_statement(statement_id: str, db: Session = Depends(get_db)):
    """Delete a single statement and its associated transactions and corrections."""
    _assert_statement_exists(statement_id, db)
    db.query(Transaction).filter(Transaction.statement_id == statement_id).delete()
    db.query(Correction).filter(Correction.statement_id == statement_id).delete()
    stmt = db.query(Statement).filter(Statement.id == statement_id).first()
    if stmt:
        db.delete(stmt)
    db.commit()
    return {"message": f"Statement {statement_id} deleted."}


@router.delete("/statements/{statement_id}/transactions/{transaction_id}")
def delete_transaction(
    statement_id: str,
    transaction_id: str,
    db: Session = Depends(get_db),
):
    """Delete an individual transaction."""
    txn = db.query(Transaction).filter(
        Transaction.statement_id == statement_id,
        Transaction.id == transaction_id,
    ).first()
    if not txn:
        raise HTTPException(status_code=404, detail="Transaction not found")
    db.delete(txn)
    db.commit()
    return {"message": "Transaction deleted"}


@router.get("/statements/{statement_id}/transactions", response_model=TransactionListResponse)
def get_transactions(
    statement_id: str,
    page: int = Query(1, ge=1),
    page_size: int = Query(50, ge=1, le=200),
    search: Optional[str] = Query(None),
    category: Optional[str] = Query(None),
    date_from: Optional[str] = Query(None),
    date_to: Optional[str] = Query(None),
    classification_method: Optional[str] = Query(None),
    review_status: Optional[str] = Query(None),
    sort_by: str = Query("date"),
    sort_order: str = Query("asc"),
    db: Session = Depends(get_db),
):
    """Get transactions for a statement with filtering and pagination."""
    _assert_statement_exists(statement_id, db)

    query = db.query(Transaction).filter(Transaction.statement_id == statement_id)

    # Filters
    if search:
        search_lower = f"%{search.lower()}%"
        query = query.filter(
            Transaction.description.ilike(search_lower) |
            Transaction.category.ilike(search_lower) |
            Transaction.original_description.ilike(search_lower)
        )
    if category:
        query = query.filter(Transaction.category == category)
    if date_from:
        query = query.filter(Transaction.date >= date_from)
    if date_to:
        query = query.filter(Transaction.date <= date_to)
    if classification_method:
        query = query.filter(Transaction.classification_method == classification_method)
    if review_status:
        query = query.filter(Transaction.review_status == review_status)

    # Sorting
    sort_col = getattr(Transaction, sort_by, Transaction.date)
    if sort_order == "desc":
        query = query.order_by(sort_col.desc())
    else:
        query = query.order_by(sort_col.asc())

    total = query.count()
    offset = (page - 1) * page_size
    transactions = query.offset(offset).limit(page_size).all()

    return TransactionListResponse(
        transactions=[_txn_to_response(t) for t in transactions],
        total=total,
        page=page,
        page_size=page_size,
        total_pages=(total + page_size - 1) // page_size,
    )


@router.put("/statements/{statement_id}/transactions/{transaction_id}", response_model=TransactionResponse)
def update_transaction(
    statement_id: str,
    transaction_id: str,
    update: TransactionUpdate,
    db: Session = Depends(get_db),
):
    """Update a transaction (category change, review status, corrections)."""
    txn = (
        db.query(Transaction)
        .filter(Transaction.id == transaction_id, Transaction.statement_id == statement_id)
        .first()
    )
    if not txn:
        raise HTTPException(status_code=404, detail="Transaction not found")

    # If category is changing, record a correction
    if update.category and update.category != txn.category:
        correction = Correction(
            transaction_id=txn.id,
            original_category=txn.category,
            original_method=txn.classification_method,
            original_confidence=txn.confidence,
            corrected_category=update.category,
        )
        db.add(correction)
        txn.category = update.category
        txn.classification_method = "manual"
        txn.confidence = None

    if update.review_status is not None:
        txn.review_status = update.review_status
    if update.description is not None:
        txn.description = update.description
    if update.date is not None:
        txn.date = update.date
    if update.debit is not None:
        txn.debit = update.debit
    if update.credit is not None:
        txn.credit = update.credit
    if update.balance is not None:
        txn.balance = update.balance

    txn.updated_at = datetime.utcnow()
    db.commit()
    db.refresh(txn)
    return _txn_to_response(txn)


# â”€â”€ Classification â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€

@router.post("/statements/{statement_id}/classify", status_code=202)
def reclassify_statement(statement_id: str, db: Session = Depends(get_db)):
    """Re-run classification on all non-manual transactions."""
    _assert_statement_exists(statement_id, db)
    from app.classification.classifier import classify_transaction

    transactions = (
        db.query(Transaction)
        .filter(
            Transaction.statement_id == statement_id,
            Transaction.classification_method != "manual",
        )
        .all()
    )
    for txn in transactions:
        result = classify_transaction(
            description=txn.description or "",
            debit=txn.debit,
            credit=txn.credit,
            db_session=db,
        )
        txn.category = result["category"]
        txn.classification_method = result["classification_method"]
        txn.confidence = result["confidence"]
        txn.review_status = result["review_status"]

    db.commit()
    return {"message": f"Reclassified {len(transactions)} transactions"}


# â”€â”€ Validation â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€

@router.get("/statements/{statement_id}/validation")
def get_validation(statement_id: str, db: Session = Depends(get_db)):
    """Get validation summary for a statement."""
    stmt = _assert_statement_exists(statement_id, db)
    transactions = (
        db.query(Transaction)
        .filter(Transaction.statement_id == statement_id)
        .order_by(Transaction.date)
        .all()
    )

    flagged = [t for t in transactions if t.validation_flags]
    flags_list = []
    for t in flagged:
        for flag in (t.validation_flags or []):
            flags_list.append({
                "transaction_id": t.id,
                "flag_type": flag,
                "message": _flag_message(flag),
                "severity": _flag_severity(flag),
            })

    # Balance reconciliation
    from app.validation.balance_checker import check_balance_reconciliation
    txn_dicts = [
        {"date": t.date, "debit": t.debit, "credit": t.credit, "balance": t.balance}
        for t in transactions
    ]
    bal_result = check_balance_reconciliation(txn_dicts, stmt.opening_balance)

    return {
        "total_transactions": len(transactions),
        "flagged_count": len(flagged),
        "balance_reconciled": bal_result["reconciled"],
        "balance_discrepancy": bal_result.get("discrepancy"),
        "flags": flags_list,
    }


# â”€â”€ Analytics â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€

@router.get("/statements/{statement_id}/analytics")
def get_analytics(statement_id: str, db: Session = Depends(get_db)):
    """Get analytics data for a statement."""
    _assert_statement_exists(statement_id, db)
    transactions = (
        db.query(Transaction)
        .filter(Transaction.statement_id == statement_id)
        .all()
    )

    # Spending by category
    cat_data: dict[str, dict] = defaultdict(lambda: {"total": 0.0, "count": 0})
    for t in transactions:
        if t.debit and t.debit > 0:
            cat_data[t.category or "Uncategorized"]["total"] += t.debit
            cat_data[t.category or "Uncategorized"]["count"] += 1

    total_spend = sum(v["total"] for v in cat_data.values()) or 1
    spending_by_category = [
        {"category": cat, "total": round(d["total"], 2), "count": d["count"],
         "percentage": round(d["total"] / total_spend * 100, 1)}
        for cat, d in sorted(cat_data.items(), key=lambda x: x[1]["total"], reverse=True)
    ]

    # Monthly trends
    monthly: dict[str, dict] = defaultdict(lambda: {"credits": 0.0, "debits": 0.0})
    for t in transactions:
        if t.date:
            mk = t.date[:7]
            monthly[mk]["credits"] += t.credit or 0
            monthly[mk]["debits"] += t.debit or 0
    monthly_trends = [
        {"month": m, "credits": round(d["credits"], 2), "debits": round(d["debits"], 2)}
        for m, d in sorted(monthly.items())
    ]

    # Top merchants
    merchant_data: dict[str, float] = defaultdict(float)
    for t in transactions:
        if t.debit and t.description:
            merchant_data[t.description[:30]] += t.debit
    top_merchants = sorted(
        [{"merchant": m, "total": round(v, 2)} for m, v in merchant_data.items()],
        key=lambda x: x["total"], reverse=True
    )[:10]

    # Classification coverage
    total = len(transactions)
    rule_based = sum(1 for t in transactions if t.classification_method == "rule_based")
    ml_based = sum(1 for t in transactions if t.classification_method == "machine_learning")
    manual = sum(1 for t in transactions if t.classification_method == "manual")
    unclassified = sum(1 for t in transactions if t.classification_method == "unclassified")
    review_required = sum(1 for t in transactions if t.review_status == "review_required")
    categorized = total - unclassified

    coverage = {
        "total": total,
        "categorized": categorized,
        "rule_based": rule_based,
        "ml_based": ml_based,
        "manual": manual,
        "unclassified": unclassified,
        "needing_review": review_required,
        "coverage_pct": round(categorized / total * 100, 1) if total > 0 else 0,
    }

    total_credits = sum(t.credit or 0 for t in transactions)
    total_debits = sum(t.debit or 0 for t in transactions)

    return {
        "spending_by_category": spending_by_category,
        "monthly_trends": monthly_trends,
        "top_merchants": top_merchants,
        "classification_coverage": coverage,
        "income_vs_expenditure": {
            "total_income": round(total_credits, 2),
            "total_expenditure": round(total_debits, 2),
            "net": round(total_credits - total_debits, 2),
        },
        "debit_vs_credit": {
            "debits": round(total_debits, 2),
            "credits": round(total_credits, 2),
        },
    }


# â”€â”€ Export â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€

@router.get("/statements/{statement_id}/export/excel")
def export_excel(statement_id: str, db: Session = Depends(get_db)):
    """Download transactions as Excel workbook."""
    stmt = _assert_statement_exists(statement_id, db)
    transactions = _get_all_transactions(statement_id, db)

    from app.export.excel_exporter import export_excel as _export
    from app.validation.balance_checker import check_balance_reconciliation

    txn_dicts = [_txn_dict(t) for t in transactions]
    validation_summary = None
    try:
        bal = check_balance_reconciliation(txn_dicts, stmt.opening_balance)
        validation_summary = {
            "balance_reconciled": bal["reconciled"],
            "flagged_count": sum(1 for t in txn_dicts if t.get("validation_flags"))
        }
    except Exception:
        pass

    xlsx_bytes = _export(stmt, txn_dicts, validation_summary)
    safe_name = (stmt.original_filename or "statement").replace(".pdf", "")
    filename = f"{safe_name}_StatementIQ.xlsx"

    return Response(
        content=xlsx_bytes,
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )


@router.get("/statements/{statement_id}/export/csv")
def export_csv(statement_id: str, db: Session = Depends(get_db)):
    """Download transactions as CSV."""
    stmt = _assert_statement_exists(statement_id, db)
    transactions = _get_all_transactions(statement_id, db)
    txn_dicts = [_txn_dict(t) for t in transactions]

    from app.export.csv_exporter import export_csv as _export
    csv_bytes = _export(txn_dicts)

    safe_name = (stmt.original_filename or "statement").replace(".pdf", "")
    filename = f"{safe_name}_StatementIQ.csv"

    return Response(
        content=csv_bytes,
        media_type="text/csv",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )


# â”€â”€ Helpers â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€

def _assert_statement_exists(statement_id: str, db: Session) -> Statement:
    stmt = db.query(Statement).filter(Statement.id == statement_id).first()
    if not stmt:
        raise HTTPException(status_code=404, detail="Statement not found")
    return stmt


def _get_all_transactions(statement_id: str, db: Session) -> list[Transaction]:
    return (
        db.query(Transaction)
        .filter(Transaction.statement_id == statement_id)
        .order_by(Transaction.date.asc())
        .all()
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


def _txn_dict(t: Transaction) -> dict:
    return {
        "id": t.id,
        "date": t.date,
        "description": t.description,
        "original_description": t.original_description,
        "debit": t.debit,
        "credit": t.credit,
        "balance": t.balance,
        "source_page": t.source_page,
        "category": t.category,
        "classification_method": t.classification_method,
        "confidence": t.confidence,
        "review_status": t.review_status,
        "validation_flags": t.validation_flags or [],
        "ocr_confidence": t.ocr_confidence,
    }


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


def _flag_message(flag: str) -> str:
    messages = {
        "missing_date": "Transaction has no date",
        "invalid_date_format": "Date format is invalid",
        "missing_amount": "No debit or credit amount found",
        "both_debit_and_credit": "Both debit and credit are populated",
        "missing_balance": "Running balance is missing",
        "balance_mismatch": "Balance does not reconcile with previous row",
        "possible_duplicate": "Possible duplicate transaction detected",
        "low_ocr_confidence": "OCR confidence below 75% â€” verify values",
        "malformed_row": "Row could not be parsed correctly",
        "unclassified": "Transaction could not be classified",
        "suspicious_amount": "Amount value appears suspicious",
    }
    return messages.get(flag, flag)


def _flag_severity(flag: str) -> str:
    errors = {"balance_mismatch", "both_debit_and_credit", "missing_amount"}
    warnings = {"low_ocr_confidence", "possible_duplicate", "malformed_row"}
    return "error" if flag in errors else "warning" if flag in warnings else "info"


