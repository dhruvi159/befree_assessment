"""Combined classification engine: Rules → ML → Unclassified."""
import logging
from typing import Optional

from app.classification.rule_engine import apply_rules
from app.classification.ml_classifier import predict
from app.classification.preprocessor import normalize_narration
from app.config import settings

logger = logging.getLogger(__name__)


def classify_transaction(
    description: str,
    debit: Optional[float] = None,
    credit: Optional[float] = None,
    db_session=None,
) -> dict:
    """
    Classify a single transaction using the decision flow:
    1. Normalize narration
    2. Apply deterministic rules (rule_based)
    3. If no rule match → ML model (machine_learning)
    4. If ML confidence < threshold → Uncategorized + review_required (unclassified)

    Returns dict with: category, classification_method, confidence, review_status
    """
    result = {
        "category": "Uncategorized",
        "classification_method": "unclassified",
        "confidence": None,
        "review_status": "pending",
    }

    if not description:
        result["review_status"] = "review_required"
        return result

    normalized = normalize_narration(description)

    # Step 1: Apply rule-based classification
    rule_result = apply_rules(description, db_session=db_session, description=normalized)
    if rule_result:
        result["category"] = rule_result["category"]
        result["classification_method"] = "rule_based"
        result["confidence"] = rule_result["confidence"]
        result["review_status"] = "pending"
        return result

    # Step 2: ML classification
    ml_result = predict(description)
    if ml_result:
        confidence = ml_result["confidence"]
        threshold = settings.confidence_threshold

        if confidence >= threshold:
            result["category"] = ml_result["category"]
            result["classification_method"] = "machine_learning"
            result["confidence"] = confidence
            result["review_status"] = "pending"
        else:
            # Below threshold → keep suggested category but flag for review
            result["category"] = "Uncategorized"
            result["classification_method"] = "unclassified"
            result["confidence"] = confidence
            result["review_status"] = "review_required"
        return result

    # Step 3: No model available → unclassified
    result["review_status"] = "review_required"
    return result


def classify_all_transactions(
    transactions: list[dict],
    db_session=None,
) -> list[dict]:
    """
    Classify a batch of transactions. Returns the same list with
    category, classification_method, confidence, review_status filled in.
    """
    for txn in transactions:
        # Skip manually classified rows
        if txn.get("classification_method") == "manual":
            continue

        cls = classify_transaction(
            description=txn.get("description", ""),
            debit=txn.get("debit"),
            credit=txn.get("credit"),
            db_session=db_session,
        )
        txn.update(cls)

    return transactions

