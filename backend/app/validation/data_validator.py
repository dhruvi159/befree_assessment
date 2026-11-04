"""Data validation engine — checks all transaction quality issues."""
import re
import logging
from typing import Optional

logger = logging.getLogger(__name__)

# Validation flag types
FLAG_MISSING_DATE = "missing_date"
FLAG_INVALID_DATE = "invalid_date_format"
FLAG_MISSING_AMOUNT = "missing_amount"
FLAG_BOTH_DEBIT_CREDIT = "both_debit_and_credit"
FLAG_MISSING_BALANCE = "missing_balance"
FLAG_BALANCE_MISMATCH = "balance_mismatch"
FLAG_DUPLICATE = "possible_duplicate"
FLAG_POSSIBLE_DUPLICATE = "possible_duplicate"
FLAG_LOW_OCR = "low_ocr_confidence"
FLAG_MALFORMED = "malformed_row"
FLAG_SUSPICIOUS_AMOUNT = "suspicious_amount"

# NOTE: FLAG_UNCLASSIFIED is intentionally NOT added here.
# Being uncategorised is not a data-quality problem — it just means the ML/rules
# engine did not recognise the merchant.  We must not set review_required solely
# because a transaction is Uncategorized, or every single row gets flagged.


def validate_transactions(
    transactions: list[dict],
    opening_balance: Optional[float] = None,
    ocr_confidence_threshold: float = 0.75,
) -> tuple[list[dict], dict]:
    """
    Run all validation checks on a list of transactions.

    Returns:
        (validated_transactions, validation_summary)
        Each transaction gets updated validation_flags.
    """
    from app.validation.balance_checker import check_balance_reconciliation

    # Balance reconciliation check
    balance_result = check_balance_reconciliation(transactions, opening_balance)
    balance_flagged_indices = set(balance_result.get("flagged_indices", []))

    for idx, txn in enumerate(transactions):
        flags = list(txn.get("validation_flags", []))

        # --- Date checks ---
        if not txn.get("date"):
            if FLAG_MISSING_DATE not in flags:
                flags.append(FLAG_MISSING_DATE)
        else:
            if not re.match(r"^\d{4}-\d{2}-\d{2}$", str(txn["date"])):
                if FLAG_INVALID_DATE not in flags:
                    flags.append(FLAG_INVALID_DATE)

        # --- Amount checks ---
        debit = txn.get("debit")
        credit = txn.get("credit")
        if debit is None and credit is None:
            if FLAG_MISSING_AMOUNT not in flags:
                flags.append(FLAG_MISSING_AMOUNT)
        if debit is not None and credit is not None and debit > 0 and credit > 0:
            if FLAG_BOTH_DEBIT_CREDIT not in flags:
                flags.append(FLAG_BOTH_DEBIT_CREDIT)

        # --- Balance check ---
        if txn.get("balance") is None:
            if FLAG_MISSING_BALANCE not in flags:
                flags.append(FLAG_MISSING_BALANCE)

        # --- Balance mismatch from reconciliation ---
        if idx in balance_flagged_indices:
            if FLAG_BALANCE_MISMATCH not in flags:
                flags.append(FLAG_BALANCE_MISMATCH)

        # --- Duplicate ---
        if FLAG_POSSIBLE_DUPLICATE in (txn.get("validation_flags") or []):
            if FLAG_DUPLICATE not in flags:
                flags.append(FLAG_DUPLICATE)

        # --- OCR confidence ---
        ocr_conf = txn.get("ocr_confidence")
        if ocr_conf is not None and ocr_conf < ocr_confidence_threshold:
            if FLAG_LOW_OCR not in flags:
                flags.append(FLAG_LOW_OCR)

        # --- Suspicious amounts (negative or unrealistically large) ---
        for amount_field in ["debit", "credit", "balance"]:
            val = txn.get(amount_field)
            if val is not None and (val < 0 or val > 100_000_000):
                if FLAG_SUSPICIOUS_AMOUNT not in flags:
                    flags.append(FLAG_SUSPICIOUS_AMOUNT)

        txn["validation_flags"] = flags

        # Only set review_required for genuine data-quality flags.
        # Do NOT flip review_status back to pending if it was manually set to approved.
        if flags and txn.get("review_status") == "pending":
            txn["review_status"] = "review_required"
        elif not flags and txn.get("review_status") == "review_required":
            # All flags cleared — reset to pending so the row no longer shows as flagged
            txn["review_status"] = "pending"

    # Build summary
    total = len(transactions)
    flagged = sum(1 for t in transactions if t.get("validation_flags"))
    summary = {
        "total_transactions": total,
        "flagged_count": flagged,
        "balance_reconciled": balance_result["reconciled"],
        "balance_discrepancy": balance_result.get("discrepancy"),
        "computed_closing_balance": balance_result.get("computed_closing_balance"),
        "flag_counts": _count_flags(transactions),
    }

    return transactions, summary


def _count_flags(transactions: list[dict]) -> dict:
    """Count occurrences of each flag type."""
    counts: dict[str, int] = {}
    for txn in transactions:
        for flag in txn.get("validation_flags", []):
            counts[flag] = counts.get(flag, 0) + 1
    return counts
