"""Model metrics endpoint."""
import logging
from datetime import datetime
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from app.database import get_db
from app.models import ModelVersion
from app.schemas import ModelMetricsResponse

logger = logging.getLogger(__name__)
router = APIRouter()


@router.get("/model/metrics", response_model=ModelMetricsResponse)
def get_model_metrics(db: Session = Depends(get_db)):
    """Get metrics for the active ML model (trained strictly on real statements)."""
    model_version = (
        db.query(ModelVersion)
        .filter(ModelVersion.is_active == True)
        .order_by(ModelVersion.created_at.desc())
        .first()
    )

    if not model_version:
        return ModelMetricsResponse(
            version="Awaiting Real Statements",
            is_active=False,
            is_synthetic=False,
            training_samples=0,
            created_at=datetime.utcnow(),
        )

    return ModelMetricsResponse(
        version=model_version.version,
        is_active=model_version.is_active,
        is_synthetic=False,
        training_samples=model_version.training_samples or 0,
        accuracy=model_version.accuracy,
        precision_macro=model_version.precision_macro,
        recall_macro=model_version.recall_macro,
        f1_macro=model_version.f1_macro,
        confusion_matrix=model_version.confusion_matrix,
        classification_report=model_version.classification_report,
        created_at=model_version.created_at,
    )


@router.post("/model/retrain", response_model=ModelMetricsResponse)
def retrain_model_on_real_data(db: Session = Depends(get_db)):
    """Retrain and evaluate TF-IDF + Logistic Regression strictly on real uploaded statement transactions."""
    from ml.train import train_on_real_data
    result = train_on_real_data(db_session=db)
    if not result:
        raise HTTPException(
            status_code=400,
            detail="Need at least 4 categorized transactions across 2 distinct categories from uploaded real statements to evaluate Logistic Regression.",
        )
    return get_model_metrics(db=db)

