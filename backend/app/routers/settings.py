"""Settings endpoint for StatementIQ configuration."""
from typing import Optional
from fastapi import APIRouter, Depends
from pydantic import BaseModel
from sqlalchemy.orm import Session
from app.database import get_db
from app.models import SystemSetting
from app.config import settings

router = APIRouter()


class SettingsResponse(BaseModel):
    retention_enabled: bool
    confidence_threshold: float


class SettingsUpdate(BaseModel):
    retention_enabled: Optional[bool] = None
    confidence_threshold: Optional[float] = None


@router.get("/settings", response_model=SettingsResponse)
def get_system_settings(db: Session = Depends(get_db)):
    """Retrieve current system settings."""
    ret_row = db.query(SystemSetting).filter(SystemSetting.key == "retention_enabled").first()
    conf_row = db.query(SystemSetting).filter(SystemSetting.key == "confidence_threshold").first()

    retention_val = (ret_row.value.lower() == "true") if ret_row else settings.retention_enabled
    threshold_val = float(conf_row.value) if conf_row else settings.confidence_threshold

    return SettingsResponse(
        retention_enabled=retention_val,
        confidence_threshold=threshold_val,
    )


@router.post("/settings", response_model=SettingsResponse)
def update_system_settings(body: SettingsUpdate, db: Session = Depends(get_db)):
    """Update system settings and persist to database."""
    if body.retention_enabled is not None:
        row = db.query(SystemSetting).filter(SystemSetting.key == "retention_enabled").first()
        if not row:
            row = SystemSetting(key="retention_enabled", value=str(body.retention_enabled))
            db.add(row)
        else:
            row.value = str(body.retention_enabled)
        settings.retention_enabled = body.retention_enabled

    if body.confidence_threshold is not None:
        row = db.query(SystemSetting).filter(SystemSetting.key == "confidence_threshold").first()
        if not row:
            row = SystemSetting(key="confidence_threshold", value=str(body.confidence_threshold))
            db.add(row)
        else:
            row.value = str(body.confidence_threshold)
        settings.confidence_threshold = body.confidence_threshold

    db.commit()
    return get_system_settings(db)

