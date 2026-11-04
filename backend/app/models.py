"""SQLAlchemy ORM models for StatementIQ."""
import uuid
from datetime import datetime

from sqlalchemy import (
    Column, String, Float, Integer, Text, DateTime, Boolean,
    ForeignKey, JSON, Enum as SAEnum
)
from sqlalchemy.orm import relationship

from app.database import Base


def generate_uuid() -> str:
    return str(uuid.uuid4())


class Statement(Base):
    __tablename__ = "statements"

    id = Column(String, primary_key=True, default=generate_uuid)
    original_filename = Column(String, nullable=False)
    stored_filename = Column(String, nullable=False)  # UUID-based safe name
    file_size = Column(Integer)
    page_count = Column(Integer)
    pdf_type = Column(String)  # text_based, scanned, mixed
    page_types = Column(JSON)  # per-page type info: [{page: 1, type: "text"}, ...]

    # Account details
    account_holder = Column(String)
    bank_name = Column(String)
    account_number = Column(String)  # stored full, masked in API responses
    ifsc_code = Column(String)
    branch = Column(String)
    statement_period_start = Column(String)
    statement_period_end = Column(String)
    opening_balance = Column(Float)
    closing_balance = Column(Float)

    # Processing status
    status = Column(String, default="uploaded")  # uploaded, detecting, extracting, standardizing, classifying, validating, completed, failed
    processing_progress = Column(Float, default=0.0)  # 0-100
    processing_message = Column(String, default="")
    error_message = Column(Text)
    password_protected = Column(Boolean, default=False)

    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    completed_at = Column(DateTime)

    # Relationships
    transactions = relationship("Transaction", back_populates="statement", cascade="all, delete-orphan")

    def __repr__(self):
        return f"<Statement {self.id[:8]} - {self.original_filename}>"


class Transaction(Base):
    __tablename__ = "transactions"

    id = Column(String, primary_key=True, default=generate_uuid)
    statement_id = Column(String, ForeignKey("statements.id"), nullable=False)

    # Core fields
    date = Column(String)  # YYYY-MM-DD
    description = Column(Text)  # cleaned description
    original_description = Column(Text)  # preserved raw text
    debit = Column(Float)
    credit = Column(Float)
    balance = Column(Float)
    source_page = Column(Integer)

    # Classification
    category = Column(String, default="Uncategorized")
    classification_method = Column(String, default="unclassified")  # rule_based, machine_learning, manual, unclassified
    confidence = Column(Float)  # nullable, 0-1

    # Review
    review_status = Column(String, default="pending")  # pending, reviewed, review_required
    validation_flags = Column(JSON, default=list)  # list of flag strings

    # OCR metadata
    ocr_confidence = Column(Float)  # per-row OCR confidence if applicable

    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationships
    statement = relationship("Statement", back_populates="transactions")
    corrections = relationship("Correction", back_populates="transaction", cascade="all, delete-orphan")

    def __repr__(self):
        return f"<Transaction {self.id[:8]} - {self.date} {self.description[:30] if self.description else ''}>"


class Correction(Base):
    """Stores user corrections for potential retraining."""
    __tablename__ = "corrections"

    id = Column(String, primary_key=True, default=generate_uuid)
    transaction_id = Column(String, ForeignKey("transactions.id"), nullable=False)

    original_category = Column(String)
    original_method = Column(String)
    original_confidence = Column(Float)
    corrected_category = Column(String, nullable=False)
    verified = Column(Boolean, default=False)  # for Tier 3 retraining

    created_at = Column(DateTime, default=datetime.utcnow)

    # Relationships
    transaction = relationship("Transaction", back_populates="corrections")


class Rule(Base):
    """User-defined classification rule overrides (stored in DB)."""
    __tablename__ = "rules"

    id = Column(String, primary_key=True, default=generate_uuid)
    category = Column(String, nullable=False)
    rule_type = Column(String, default="keyword")  # keyword, regex
    pattern = Column(String, nullable=False)
    priority = Column(Integer, default=50)  # higher = checked first
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)


class ModelVersion(Base):
    """Tracks ML model versions."""
    __tablename__ = "model_versions"

    id = Column(String, primary_key=True, default=generate_uuid)
    version = Column(String, nullable=False)
    filename = Column(String, nullable=False)
    training_samples = Column(Integer)
    accuracy = Column(Float)
    precision_macro = Column(Float)
    recall_macro = Column(Float)
    f1_macro = Column(Float)
    confusion_matrix = Column(JSON)
    classification_report = Column(JSON)
    is_active = Column(Boolean, default=True)
    is_synthetic = Column(Boolean, default=False)
    metadata_json = Column(JSON)  # extra info
    created_at = Column(DateTime, default=datetime.utcnow)


class SystemSetting(Base):
    """Persistent system settings (retention, threshold, etc.)."""
    __tablename__ = "system_settings"

    key = Column(String, primary_key=True)
    value = Column(String, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)


