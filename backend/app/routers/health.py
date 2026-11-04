"""Health check endpoint."""
import os
from fastapi import APIRouter
from app.schemas import HealthResponse

router = APIRouter()


@router.get("/health", response_model=HealthResponse)
def health_check():
    """Check system health and dependency availability."""
    from app.config import settings
    from app.classification.ml_classifier import is_model_available

    # Tesseract
    tesseract_ok = os.path.exists(settings.tesseract_cmd)

    # Poppler
    poppler_ok = os.path.isdir(settings.poppler_path)

    # ML model
    ml_ok = is_model_available()

    # DB
    db_ok = True
    try:
        from app.database import engine
        with engine.connect() as conn:
            conn.execute(engine.dialect.has_table.__doc__ and None or __import__("sqlalchemy").text("SELECT 1"))
    except Exception:
        db_ok = False

    return HealthResponse(
        status="healthy",
        version="1.0.0",
        tesseract_available=tesseract_ok,
        poppler_available=poppler_ok,
        ml_model_loaded=ml_ok,
        database_connected=db_ok,
    )

