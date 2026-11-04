"""Standardize raw extracted transactions to unified schema."""
import hashlib
import logging
import re
from typing import Optional

from app.utils.formatting import parse_date, parse_amount

logger = logging.getLogger(__name__)

# Flags
FLAG_MISSING_DATE = "missing_date"
FLAG_INVALID_DATE = "invalid_date"
FLAG_MISSING_AMOUNT = "missing_amount"
FLAG_BOTH_DEBIT_CREDIT = "both_debit_and_credit"
FLAG_MISSING_BALANCE = "missing_balance"
FLAG_MALFORMED_ROW = "malformed_row"
FLAG_POSSIBLE_DUPLICATE = "possible_duplicate"
FLAG_LOW_OCR = "low_ocr_confidence"


def standardize_transactions(
    raw_transactions: list[dict],
    statement_id: str,
) -> list[dict]:
    """
    Normalize raw extracted transactions to the unified schema.
    Flags malformed rows instead of discarding them.

    Returns list of standardized transaction dicts ready for DB insertion.
    """
    seen_hashes: set[str] = set()
    standardized = []

    for idx, raw in enumerate(raw_transactions):
        txn = {
            "statement_id": statement_id,
            "date": None,
            "description": "",
            "original_description": "",
            "debit": None,
            "credit": None,
            "balance": None,
            "source_page": raw.get("source_page", 0),
            "category": "Uncategorized",
            "classification_method": "unclassified",
            "confidence": None,
            "review_status": "pending",
            "validation_flags": [],
            "ocr_confidence": raw.get("ocr_confidence"),
        }
        flags = []

        # --- Date ---
        raw_date = raw.get("date")
        if raw_date:
            parsed = parse_date(str(raw_date))
            if parsed:
                txn["date"] = parsed
            else:
                txn["date"] = None
                flags.append(FLAG_INVALID_DATE)
        else:
            flags.append(FLAG_MISSING_DATE)

        # --- Description ---
        desc = raw.get("description", raw.get("original_description", ""))
        orig_desc = raw.get("original_description", desc)
        txn["description"] = _clean_description(str(desc)) if desc else ""
        txn["original_description"] = str(orig_desc).strip() if orig_desc else ""

        # --- Amounts ---
        raw_debit = raw.get("debit")
        raw_credit = raw.get("credit")
        raw_balance = raw.get("balance")

        debit = parse_amount(raw_debit) if raw_debit is not None else None
        credit = parse_amount(raw_credit) if raw_credit is not None else None
        balance = parse_amount(raw_balance) if raw_balance is not None else None

        # Normalize negative values
        if debit is not None and debit < 0:
            credit = abs(debit)
            debit = None
        if credit is not None and credit < 0:
            debit = abs(credit)
            credit = None

        txn["debit"] = debit
        txn["credit"] = credit
        txn["balance"] = balance

        # Validate amounts
        if debit is None and credit is None:
            flags.append(FLAG_MISSING_AMOUNT)
        if debit is not None and credit is not None and debit > 0 and credit > 0:
            flags.append(FLAG_BOTH_DEBIT_CREDIT)
        if balance is None:
            flags.append(FLAG_MISSING_BALANCE)

        # --- Low OCR confidence ---
        ocr_conf = txn["ocr_confidence"]
        if ocr_conf is not None and ocr_conf < 0.75:
            flags.append(FLAG_LOW_OCR)

        # --- Duplicate detection ---
        dup_key = _make_dup_key(txn["date"], txn["debit"], txn["credit"], txn["description"])
        if dup_key in seen_hashes:
            flags.append(FLAG_POSSIBLE_DUPLICATE)
        else:
            seen_hashes.add(dup_key)

        # --- Malformed row check ---
        if not txn["date"] and not txn["description"] and debit is None and credit is None:
            flags.append(FLAG_MALFORMED_ROW)

        txn["validation_flags"] = flags

        # Set review_status for flagged rows
        if flags:
            txn["review_status"] = "review_required"

        standardized.append(txn)

    logger.info(f"Standardized {len(standardized)} transactions for statement {statement_id[:8]}")
    return standardized


def _clean_description(text: str) -> str:
    """Clean and normalize a transaction description."""
    if not text:
        return ""
    # Strip leading/trailing whitespace
    text = text.strip()
    # Normalize whitespace
    text = re.sub(r"\s+", " ", text)
    # Remove common noise characters
    text = text.strip(".,;:-|/")
    return text


def _make_dup_key(date, debit, credit, description) -> str:
    """Create a hash key for duplicate detection."""
    amount = debit or credit or 0
    key = f"{date}|{amount:.2f}|{(description or '')[:50]}"
    return hashlib.md5(key.encode()).hexdigest()

