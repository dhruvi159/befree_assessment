"""Rules management endpoints."""
import logging
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.database import get_db
from app.models import Rule
from app.schemas import RuleCreate, RuleResponse, RuleUpdate, RulesListResponse
from app.classification.rule_engine import invalidate_rule_cache

logger = logging.getLogger(__name__)
router = APIRouter()


@router.get("/rules", response_model=RulesListResponse)
def get_rules(db: Session = Depends(get_db)):
    """Get all classification rules (DB overrides only)."""
    rules = db.query(Rule).order_by(Rule.priority.desc(), Rule.created_at).all()
    return RulesListResponse(
        rules=[_rule_response(r) for r in rules],
        total=len(rules)
    )


@router.post("/rules", response_model=RuleResponse, status_code=201)
def create_rule(rule_in: RuleCreate, db: Session = Depends(get_db)):
    """Create a new classification rule."""
    rule = Rule(
        category=rule_in.category,
        rule_type=rule_in.rule_type,
        pattern=rule_in.pattern,
        priority=rule_in.priority,
        is_active=rule_in.is_active,
    )
    db.add(rule)
    db.commit()
    db.refresh(rule)
    invalidate_rule_cache()
    return _rule_response(rule)


@router.put("/rules/{rule_id}", response_model=RuleResponse)
def update_rule(rule_id: str, rule_in: RuleUpdate, db: Session = Depends(get_db)):
    """Update an existing rule."""
    rule = db.query(Rule).filter(Rule.id == rule_id).first()
    if not rule:
        raise HTTPException(status_code=404, detail="Rule not found")

    for field, value in rule_in.model_dump(exclude_unset=True).items():
        setattr(rule, field, value)

    db.commit()
    db.refresh(rule)
    invalidate_rule_cache()
    return _rule_response(rule)


@router.delete("/rules/{rule_id}", status_code=204)
def delete_rule(rule_id: str, db: Session = Depends(get_db)):
    """Delete a rule."""
    rule = db.query(Rule).filter(Rule.id == rule_id).first()
    if not rule:
        raise HTTPException(status_code=404, detail="Rule not found")
    db.delete(rule)
    db.commit()
    invalidate_rule_cache()


def _rule_response(r: Rule) -> RuleResponse:
    return RuleResponse(
        id=r.id,
        category=r.category,
        rule_type=r.rule_type,
        pattern=r.pattern,
        priority=r.priority,
        is_active=r.is_active,
        created_at=r.created_at,
        updated_at=r.updated_at,
    )

