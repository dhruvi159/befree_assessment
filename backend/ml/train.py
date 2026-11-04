"""
ML Model Training Script for StatementIQ.
Trains TF-IDF + Logistic Regression strictly on real statement transactions uploaded by the user.
Zero synthetic data — only real bank statements are used.
"""
import json
import logging
import sys
import uuid
from datetime import datetime
from pathlib import Path
from typing import Optional

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger(__name__)

# Add backend to path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))


def train_on_real_data(db_session=None) -> Optional[dict]:
    """
    Train and evaluate TF-IDF + Logistic Regression strictly on real uploaded statement transactions.
    Returns metrics dict if trained, or None if insufficient real data.
    """
    from app.config import settings
    from app.classification.preprocessor import normalize_narration
    from app.classification.ml_classifier import reload_model
    from app.database import SessionLocal, init_db
    from app.models import Transaction, ModelVersion, Statement

    close_db = False
    if db_session is None:
        init_db()
        db_session = SessionLocal()
        close_db = True

    try:
        import joblib
        import numpy as np
        from sklearn.linear_model import LogisticRegression
        from sklearn.feature_extraction.text import TfidfVectorizer
        from sklearn.pipeline import Pipeline
        from sklearn.model_selection import StratifiedShuffleSplit, train_test_split
        from sklearn.metrics import (
            classification_report, confusion_matrix,
            precision_score, recall_score, f1_score, accuracy_score
        )
    except ImportError as e:
        logger.error(f"Required package missing: {e}. Run: pip install -r requirements.txt")
        if close_db:
            db_session.close()
        return None

    try:
        # Query real transactions from uploaded statements that have been categorized
        query = (
            db_session.query(Transaction.description, Transaction.category)
            .filter(
                Transaction.description.isnot(None),
                Transaction.category.isnot(None),
                Transaction.category != "Uncategorized",
                Transaction.category != "",
            )
        )
        rows = query.all()

        if not rows or len(rows) < 4:
            logger.info("Insufficient real statement transactions to train Logistic Regression (minimum 4 categorized transactions required).")
            return None

        # Prepare normalized texts and labels from real transactions
        texts = []
        labels = []
        for desc, cat in rows:
            norm = normalize_narration(desc)
            if norm and cat:
                texts.append(norm)
                labels.append(cat)

        unique_labels = sorted(set(labels))
        if len(unique_labels) < 2:
            logger.info(f"Only 1 unique category found ({unique_labels[0]}). Need at least 2 distinct categories to train Logistic Regression classifier.")
            return None

        logger.info(f"Training Logistic Regression on {len(texts)} real statement transactions across {len(unique_labels)} categories: {unique_labels}")

        # Train / Test split on real transactions
        # If at least 2 samples per class, use stratified split; otherwise random split
        min_class_count = min(labels.count(c) for c in unique_labels)
        test_size = 0.2 if len(texts) >= 15 else (1.0 / len(texts) if len(texts) <= 5 else 0.25)

        if min_class_count >= 2 and len(texts) >= 10:
            try:
                sss = StratifiedShuffleSplit(n_splits=1, test_size=test_size, random_state=42)
                train_idx, test_idx = next(sss.split(texts, labels))
                X_train = [texts[i] for i in train_idx]
                y_train = [labels[i] for i in train_idx]
                X_test = [texts[i] for i in test_idx]
                y_test = [labels[i] for i in test_idx]
            except Exception:
                X_train, X_test, y_train, y_test = train_test_split(
                    texts, labels, test_size=test_size, random_state=42
                )
        else:
            X_train, X_test, y_train, y_test = train_test_split(
                texts, labels, test_size=test_size, random_state=42
            )

        logger.info(f"Real Data Split — Train: {len(X_train)}, Test: {len(X_test)}")

        # Build TF-IDF + Logistic Regression pipeline
        pipeline = Pipeline([
            ("tfidf", TfidfVectorizer(
                analyzer="word",
                ngram_range=(1, 2),
                max_features=5000,
                sublinear_tf=True,
                min_df=1,
            )),
            ("clf", LogisticRegression(
                max_iter=1000,
                C=2.0,
                class_weight="balanced",
                solver="lbfgs",
                random_state=42,
            )),
        ])

        pipeline.fit(X_train, y_train)

        # Evaluate strictly on real test statements
        y_pred = pipeline.predict(X_test)

        accuracy = float(accuracy_score(y_test, y_pred))
        precision = float(precision_score(y_test, y_pred, average="macro", zero_division=0))
        recall = float(recall_score(y_test, y_pred, average="macro", zero_division=0))
        f1 = float(f1_score(y_test, y_pred, average="macro", zero_division=0))

        logger.info(f"Real Statements Model Evaluated:")
        logger.info(f"  Accuracy:  {accuracy:.1%}")
        logger.info(f"  Precision: {precision:.1%} (macro)")
        logger.info(f"  Recall:    {recall:.1%} (macro)")
        logger.info(f"  F1:        {f1:.1%} (macro)")

        # Confusion matrix
        classes = sorted(set(labels))
        cm = confusion_matrix(y_test, y_pred, labels=classes)
        cm_dict = {
            "labels": classes,
            "matrix": cm.tolist(),
        }

        # Classification report
        report = classification_report(y_test, y_pred, output_dict=True, zero_division=0)

        # Save model artifact
        version = f"v1.0.0-real-statements"
        model_filename = f"model_{version}.joblib"
        model_path = settings.ml_models_dir / model_filename
        settings.ml_models_dir.mkdir(parents=True, exist_ok=True)

        joblib.dump(pipeline, str(model_path))

        # Save metrics JSON
        metrics = {
            "version": version,
            "filename": model_filename,
            "training_samples": len(X_train),
            "test_samples": len(X_test),
            "accuracy": accuracy,
            "precision_macro": precision,
            "recall_macro": recall,
            "f1_macro": f1,
            "confusion_matrix": cm_dict,
            "classification_report": report,
            "is_synthetic": False,
            "trained_at": datetime.utcnow().isoformat(),
            "source": "real_uploaded_statements",
        }

        metrics_path = settings.ml_models_dir / f"metrics_{version}.json"
        with open(metrics_path, "w") as f:
            json.dump(metrics, f, indent=2)

        # Save / Update ModelVersion in database
        db_session.query(ModelVersion).update({"is_active": False})

        mv = ModelVersion(
            id=str(uuid.uuid4()),
            version=version,
            filename=model_filename,
            training_samples=len(X_train),
            accuracy=accuracy,
            precision_macro=precision,
            recall_macro=recall,
            f1_macro=f1,
            confusion_matrix=cm_dict,
            classification_report={k: v for k, v in report.items() if k != "macro avg"},
            is_active=True,
            is_synthetic=False,
            metadata_json={
                "source": "real_uploaded_statements",
                "test_size": len(X_test),
                "total_real_transactions": len(texts),
            },
        )
        db_session.add(mv)
        db_session.commit()

        # Reload active model in memory
        reload_model()
        logger.info(f"Active model successfully updated from real statement transactions: {version}")
        return metrics

    except Exception as e:
        logger.exception(f"Error training model on real statements: {e}")
        return None
    finally:
        if close_db:
            db_session.close()


def train():
    """CLI entrypoint."""
    train_on_real_data()


if __name__ == "__main__":
    train()
