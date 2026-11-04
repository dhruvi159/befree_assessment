"""
Pipeline orchestrator â€” coordinates the full processing pipeline.
Runs as a FastAPI BackgroundTask.
"""
import logging
import os
import uuid
from datetime import datetime
from pathlib import Path
from typing import Optional

logger = logging.getLogger(__name__)


def process_statement(
    statement_id: str,
    pdf_path: str,
    password: Optional[str] = None,
    db_session=None,
) -> None:
    """
    Full pipeline: Detect â†’ Extract â†’ Standardize â†’ Classify â†’ Validate â†’ Save.
    Updates Statement status at each step.
    """
    from app.models import Statement, Transaction
    from app.pipeline.detector import detect_pdf_type
    from app.pipeline.text_extractor import extract_text_pdf
    from app.pipeline.ocr_engine import ocr_pdf_pages
    from app.pipeline.standardizer import standardize_transactions
    from app.classification.classifier import classify_all_transactions
    from app.validation.data_validator import validate_transactions

    # Helper to update status
    def _update_status(status: str, progress: float, message: str = ""):
        stmt = db_session.query(Statement).filter(Statement.id == statement_id).first()
        if stmt:
            stmt.status = status
            stmt.processing_progress = progress
            stmt.processing_message = message
            stmt.updated_at = datetime.utcnow()
            db_session.commit()

    def _fail(error_msg: str):
        stmt = db_session.query(Statement).filter(Statement.id == statement_id).first()
        if stmt:
            stmt.status = "failed"
            stmt.error_message = error_msg
            stmt.updated_at = datetime.utcnow()
            db_session.commit()

    try:
        # â”€â”€ Stage 1: Detect â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
        _update_status("detecting", 10.0, "Detecting PDF type...")
        detection = detect_pdf_type(pdf_path, password=password)

        if detection.get("error"):
            _fail(detection["error"])
            return

        # Update statement with detection results
        stmt = db_session.query(Statement).filter(Statement.id == statement_id).first()
        if not stmt:
            return
        stmt.pdf_type = detection["pdf_type"]
        stmt.page_count = detection["page_count"]
        stmt.page_types = detection["page_types"]
        stmt.password_protected = detection["password_protected"]
        db_session.commit()

        page_types = detection["page_types"]

        # â”€â”€ Stage 2: Extract â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
        _update_status("extracting", 30.0, "Extracting text...")

        raw_transactions = []
        account_details = {}
        bank_name = "Unknown"

        # Text-based extraction
        text_pages = [p for p in page_types if p["type"] == "text"]
        if text_pages:
            text_result = extract_text_pdf(pdf_path, page_types, password=password)
            if text_result.get("error") and not text_result.get("raw_transactions"):
                logger.warning(f"Text extraction warning: {text_result['error']}")
            account_details = text_result.get("account_details", {})
            bank_name = text_result.get("bank_name", "Unknown")
            raw_transactions.extend(text_result.get("raw_transactions", []))

        # OCR for scanned pages
        scanned_pages = [p for p in page_types if p["type"] == "scanned"]
        if scanned_pages:
            total_scanned = len(scanned_pages)
            def _ocr_prog(curr, tot):
                p = 35.0 + (curr / max(1, tot)) * 18.0
                _update_status("extracting", p, f"Running OCR on page {curr} of {tot}...")

            _update_status("extracting", 35.0, f"Running OCR on {total_scanned} scanned page(s)...")
            ocr_result = ocr_pdf_pages(
                pdf_path,
                page_types,
                password=password,
                progress_callback=_ocr_prog,
            )
            if ocr_result.get("error"):
                logger.warning(f"OCR warning: {ocr_result['error']}")
            raw_transactions.extend(ocr_result.get("raw_transactions", []))

            # Update account details from OCR if text extraction was empty
            if not account_details and ocr_result.get("account_details"):
                account_details = ocr_result["account_details"]
                if bank_name == "Unknown":
                    bank_name = ocr_result.get("bank_name", "Unknown")

            # Update OCR results on statement
            stmt = db_session.query(Statement).filter(Statement.id == statement_id).first()
            if stmt and ocr_result.get("ocr_results"):
                avg_conf = sum(r.get("confidence", 0) for r in ocr_result["ocr_results"])
                avg_conf /= len(ocr_result["ocr_results"])
                stmt.processing_message = f"OCR completed ({avg_conf:.0%} avg conf). {len(raw_transactions)} rows found."
                db_session.commit()

        # Update account details on statement
        stmt = db_session.query(Statement).filter(Statement.id == statement_id).first()
        if stmt and account_details:
            from app.utils.masking import mask_account_number
            stmt.account_holder = account_details.get("account_holder")
            stmt.bank_name = account_details.get("bank_name") or bank_name
            stmt.account_number = account_details.get("account_number")
            stmt.ifsc_code = account_details.get("ifsc_code")
            stmt.branch = account_details.get("branch")
            stmt.statement_period_start = account_details.get("statement_period_start")
            stmt.statement_period_end = account_details.get("statement_period_end")
            stmt.opening_balance = account_details.get("opening_balance")
            stmt.closing_balance = account_details.get("closing_balance")
            db_session.commit()

        # â”€â”€ Stage 3: Standardize â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
        _update_status("standardizing", 55.0, f"Standardizing {len(raw_transactions)} transactions...")
        standardized = standardize_transactions(raw_transactions, statement_id)

        # â”€â”€ Stage 4: Classify â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
        _update_status("classifying", 70.0, f"Classifying {len(standardized)} transactions...")
        classified = classify_all_transactions(standardized, db_session=db_session)

        # â”€â”€ Stage 5: Validate â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
        _update_status("validating", 85.0, "Validating data...")
        stmt = db_session.query(Statement).filter(Statement.id == statement_id).first()
        opening_balance = stmt.opening_balance if stmt else None
        validated, validation_summary = validate_transactions(classified, opening_balance)

        # â”€â”€ Save to DB â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
        _update_status("saving", 95.0, "Saving results...")

        # Clear existing transactions (for re-processing)
        db_session.query(Transaction).filter(
            Transaction.statement_id == statement_id
        ).delete()
        db_session.commit()

        # Bulk insert transactions
        txn_objects = []
        for txn_data in validated:
            txn = Transaction(
                id=str(uuid.uuid4()),
                statement_id=statement_id,
                date=txn_data.get("date"),
                description=txn_data.get("description", ""),
                original_description=txn_data.get("original_description", ""),
                debit=txn_data.get("debit"),
                credit=txn_data.get("credit"),
                balance=txn_data.get("balance"),
                source_page=txn_data.get("source_page"),
                category=txn_data.get("category", "Uncategorized"),
                classification_method=txn_data.get("classification_method", "unclassified"),
                confidence=txn_data.get("confidence"),
                review_status=txn_data.get("review_status", "pending"),
                validation_flags=txn_data.get("validation_flags", []),
                ocr_confidence=txn_data.get("ocr_confidence"),
            )
            txn_objects.append(txn)

        db_session.bulk_save_objects(txn_objects)
        db_session.commit()

        # ── Derive opening/closing balance from transactions if not extracted ──
        stmt = db_session.query(Statement).filter(Statement.id == statement_id).first()
        if stmt and txn_objects:
            # Sort by date to get first and last
            dated = [t for t in txn_objects if t.date and t.balance is not None]
            dated_sorted = sorted(dated, key=lambda t: t.date)
            if dated_sorted:
                last_txn = dated_sorted[-1]
                if stmt.closing_balance is None:
                    stmt.closing_balance = last_txn.balance
                # Opening balance = closing balance of last txn - net of all txns
                if stmt.opening_balance is None:
                    total_credits = sum(t.credit or 0 for t in txn_objects)
                    total_debits = sum(t.debit or 0 for t in txn_objects)
                    stmt.opening_balance = round(last_txn.balance - total_credits + total_debits, 2)
            db_session.commit()

        # Mark complete
        stmt = db_session.query(Statement).filter(Statement.id == statement_id).first()
        if stmt:
            stmt.status = "completed"
            stmt.processing_progress = 100.0
            stmt.processing_message = (
                f"Processed {len(txn_objects)} transactions. "
                f"{validation_summary.get('flagged_count', 0)} flagged."
            )
            stmt.completed_at = datetime.utcnow()
            db_session.commit()

        logger.info(f"Statement {statement_id[:8]} processed: {len(txn_objects)} transactions")

        # Automatically train & evaluate Logistic Regression model on real uploaded statements
        try:
            from ml.train import train_on_real_data
            train_on_real_data(db_session=db_session)
        except Exception as e:
            logger.warning(f"Could not auto-train model on real statements: {e}")

        # Clean up uploaded file
        try:
            if os.path.exists(pdf_path):
                os.remove(pdf_path)
                logger.info(f"Cleaned up uploaded file: {pdf_path}")
        except Exception as e:
            logger.warning(f"Could not delete uploaded file {pdf_path}: {e}")

    except Exception as e:
        logger.exception(f"Pipeline error for statement {statement_id}")
        _fail(f"Processing error: {str(e)}")

        # Still try to clean up
        try:
            if os.path.exists(pdf_path):
                os.remove(pdf_path)
        except Exception:
            pass


