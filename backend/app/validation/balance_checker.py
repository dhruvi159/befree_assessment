"""Balance reconciliation validator."""
import logging
from typing import Optional

logger = logging.getLogger(__name__)

BALANCE_TOLERANCE = 0.02  # allow 2 paise rounding tolerance


def check_balance_reconciliation(
    transactions: list[dict],
    opening_balance: Optional[float],
) -> dict:
    """
    Validate balance consistency across all transactions.
    expected_balance = previous_balance - debit + credit

    Returns:
        {
            "reconciled": bool,
            "discrepancy": float | None,
            "flagged_indices": list[int],  # row indices with balance errors
            "opening_balance_used": float | None,
            "computed_closing_balance": float | None,
        }
    """
    result = {
        "reconciled": True,
        "discrepancy": None,
        "flagged_indices": [],
        "opening_balance_used": opening_balance,
        "computed_closing_balance": None,
    }

    if not transactions:
        return result

    # Sort by date to ensure correct order
    def sort_key(t):
        return t.get("date") or ""

    sorted_txns = sorted(enumerate(transactions), key=lambda x: sort_key(x[1]))

    prev_balance = opening_balance
    flagged = []

    for original_idx, txn in sorted_txns:
        debit = txn.get("debit") or 0.0
        credit = txn.get("credit") or 0.0
        balance = txn.get("balance")

        if balance is None:
            continue  # skip rows without balance (already flagged elsewhere)

        if prev_balance is not None:
            expected = prev_balance - debit + credit
            diff = abs(expected - balance)
            if diff > BALANCE_TOLERANCE:
                flagged.append({
                    "index": original_idx,
                    "expected": round(expected, 2),
                    "extracted": round(balance, 2),
                    "discrepancy": round(diff, 2),
                })

        prev_balance = balance

    result["computed_closing_balance"] = round(prev_balance, 2) if prev_balance is not None else None
    result["flagged_indices"] = [f["index"] for f in flagged]

    if flagged:
        result["reconciled"] = False
        result["discrepancy"] = max(f["discrepancy"] for f in flagged)
        result["balance_errors"] = flagged
    else:
        result["balance_errors"] = []

    return result

