"""ML classifier using TF-IDF + Logistic Regression."""
import logging
import os
from pathlib import Path
from typing import Optional

logger = logging.getLogger(__name__)

_model = None
_model_loaded = False
_model_version = None


def _get_model_path() -> Optional[Path]:
    """Find the active ML model file."""
    from app.config import settings
    models_dir = settings.ml_models_dir
    # Look for the active model
    model_files = sorted(models_dir.glob("model_v*.joblib"), reverse=True)
    if model_files:
        return model_files[0]
    return None


def load_model():
    """Load the ML model from disk."""
    global _model, _model_loaded, _model_version

    try:
        import joblib
        model_path = _get_model_path()
        if not model_path or not model_path.exists():
            logger.warning("No ML model found. Run ml/train.py to train a model.")
            _model = None
            _model_loaded = True
            return

        _model = joblib.load(str(model_path))
        _model_version = model_path.stem
        _model_loaded = True
        logger.info(f"Loaded ML model: {model_path.name}")
    except Exception as e:
        logger.warning(f"Failed to load ML model: {e}")
        _model = None
        _model_loaded = True


def predict(narration: str) -> Optional[dict]:
    """
    Predict category for a narration using the ML model.

    Returns dict with {category, confidence, method} or None if model unavailable.
    Confidence is the model's probability score (not guaranteed accuracy).
    """
    global _model, _model_loaded

    if not _model_loaded:
        load_model()

    if _model is None:
        return None

    if not narration or not narration.strip():
        return None

    try:
        from app.classification.preprocessor import normalize_narration
        normalized = normalize_narration(narration)
        if not normalized:
            return None

        proba = _model.predict_proba([normalized])[0]
        predicted_class_idx = proba.argmax()
        predicted_category = _model.classes_[predicted_class_idx]
        confidence = float(proba[predicted_class_idx])

        return {
            "category": predicted_category,
            "confidence": confidence,
            "classification_method": "machine_learning",
            "model_version": _model_version,
        }
    except Exception as e:
        logger.warning(f"ML prediction error: {e}")
        return None


def reload_model():
    """Force reload the model (call after retraining)."""
    global _model_loaded
    _model_loaded = False
    load_model()


def is_model_available() -> bool:
    """Check if a trained model is available."""
    if not _model_loaded:
        load_model()
    return _model is not None

