"""Rule-based classification engine."""
import logging
import re
from pathlib import Path
from typing import Optional

import yaml

from app.classification.preprocessor import normalize_narration
from app.config import settings

logger = logging.getLogger(__name__)

# In-memory rule cache
_yaml_rules: list[dict] = []
_rules_loaded = False


def _load_yaml_rules() -> list[dict]:
    """Load classification rules from categories.yaml."""
    global _yaml_rules, _rules_loaded
    if _rules_loaded:
        return _yaml_rules

    config_path = settings.config_dir / "categories.yaml"
    if not config_path.exists():
        logger.warning(f"categories.yaml not found at {config_path}")
        return []

    with open(config_path, "r", encoding="utf-8") as f:
        data = yaml.safe_load(f)

    rules = []
    for cat in data.get("categories", []):
        name = cat["name"]
        priority = cat.get("priority", 50)

        for kw in cat.get("keywords", []):
            rules.append({
                "category": name,
                "rule_type": "keyword",
                "pattern": kw.lower(),
                "priority": priority,
                "source": "yaml",
            })

        for regex in cat.get("regex_patterns", []):
            rules.append({
                "category": name,
                "rule_type": "regex",
                "pattern": regex,
                "priority": priority,
                "source": "yaml",
            })

    # Sort by priority descending (higher priority checked first)
    rules.sort(key=lambda r: r["priority"], reverse=True)
    _yaml_rules = rules
    _rules_loaded = True
    logger.info(f"Loaded {len(rules)} rules from categories.yaml")
    return rules


def _load_db_rules(db_session) -> list[dict]:
    """Load user-defined rules from SQLite (overrides)."""
    try:
        from app.models import Rule
        db_rules = db_session.query(Rule).filter(Rule.is_active == True).all()
        return [
            {
                "category": r.category,
                "rule_type": r.rule_type,
                "pattern": r.pattern.lower() if r.rule_type == "keyword" else r.pattern,
                "priority": r.priority,
                "source": "db",
            }
            for r in db_rules
        ]
    except Exception as e:
        logger.warning(f"Could not load DB rules: {e}")
        return []


def apply_rules(
    narration: str,
    db_session=None,
    description: str = "",
) -> Optional[dict]:
    """
    Apply classification rules to a normalized narration.

    Returns dict with {category, confidence, method, matched_rule} or None.
    DB rules (user overrides) take precedence over YAML rules.
    """
    if not narration and not description:
        return None

    normalized = normalize_narration(narration or description)
    if not normalized:
        return None

    # Load rules
    yaml_rules = _load_yaml_rules()
    db_rules = _load_db_rules(db_session) if db_session else []

    # DB rules take priority
    all_rules = db_rules + yaml_rules

    for rule in all_rules:
        category = rule["category"]
        if category == "Uncategorized":
            continue

        pattern = rule["pattern"]
        rule_type = rule["rule_type"]

        try:
            if rule_type == "keyword":
                if pattern in normalized:
                    confidence = 1.0 if rule["source"] == "db" else 0.95
                    return {
                        "category": category,
                        "confidence": confidence,
                        "classification_method": "rule_based",
                        "matched_rule": pattern,
                    }
            elif rule_type == "regex":
                if re.search(pattern, narration or description, re.IGNORECASE):
                    confidence = 1.0 if rule["source"] == "db" else 0.95
                    return {
                        "category": category,
                        "confidence": confidence,
                        "classification_method": "rule_based",
                        "matched_rule": pattern,
                    }
        except re.error as e:
            logger.warning(f"Invalid regex pattern '{pattern}': {e}")
            continue

    return None


def invalidate_rule_cache():
    """Call when rules are updated via API."""
    global _rules_loaded
    _rules_loaded = False

