"""CSV exporter using pandas."""
import io
import logging
from typing import Optional

logger = logging.getLogger(__name__)

try:
    import pandas as pd
    PANDAS_AVAILABLE = True
except ImportError:
    PANDAS_AVAILABLE = False
    logger.warning("pandas not available.")


def export_csv(transactions: list) -> bytes:
    """
    Export transactions to CSV format.
    Returns bytes of the CSV content.
    """
    if not PANDAS_AVAILABLE:
        raise RuntimeError("pandas not installed")

    if not transactions:
        # Return empty CSV with headers
        headers = "date,description,original_description,debit,credit,balance,category,classification_method,confidence,review_status,validation_flags,source_page\n"
        return headers.encode("utf-8-sig")

    rows = []
    for txn in transactions:
        flags = txn.get("validation_flags") or []
        conf = txn.get("confidence")
        rows.append({
            "date": txn.get("date", ""),
            "description": txn.get("description", ""),
            "original_description": txn.get("original_description", ""),
            "debit": txn.get("debit"),
            "credit": txn.get("credit"),
            "balance": txn.get("balance"),
            "category": txn.get("category", ""),
            "classification_method": txn.get("classification_method", ""),
            "confidence": round(conf * 100, 1) if conf is not None else None,
            "review_status": txn.get("review_status", ""),
            "validation_flags": "|".join(flags),
            "source_page": txn.get("source_page"),
        })

    df = pd.DataFrame(rows)
    output = io.BytesIO()
    df.to_csv(output, index=False, encoding="utf-8-sig")
    return output.getvalue()

