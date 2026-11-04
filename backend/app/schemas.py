"""Pydantic schemas for StatementIQ API."""
from __future__ import annotations

from datetime import datetime
from typing import Optional

from pydantic import BaseModel, Field


# ── Statement ──────────────────────────────────────────
class StatementBase(BaseModel):
    original_filename: str
    file_size: Optional[int] = None
    page_count: Optional[int] = None
    pdf_type: Optional[str] = None

class PageTypeInfo(BaseModel):
    page: int
    type: str  # text, scanned

class StatementResponse(StatementBase):
    id: str
    status: str
    processing_progress: float
    processing_message: str = ""
    error_message: Optional[str] = None
    page_types: Optional[list[PageTypeInfo]] = None
    password_protected: bool = False
    account_holder: Optional[str] = None
    bank_name: Optional[str] = None
    account_number_masked: Optional[str] = None  # last 4 digits only
    ifsc_code: Optional[str] = None
    branch: Optional[str] = None
    statement_period_start: Optional[str] = None
    statement_period_end: Optional[str] = None
    opening_balance: Optional[float] = None
    closing_balance: Optional[float] = None
    created_at: datetime
    completed_at: Optional[datetime] = None

    class Config:
        from_attributes = True

class StatementStatusResponse(BaseModel):
    id: str
    status: str
    processing_progress: float
    processing_message: str = ""
    error_message: Optional[str] = None
    pdf_type: Optional[str] = None
    page_types: Optional[list[PageTypeInfo]] = None
    page_count: Optional[int] = None


# ── Transaction ────────────────────────────────────────
class TransactionBase(BaseModel):
    date: Optional[str] = None
    description: Optional[str] = None
    original_description: Optional[str] = None
    debit: Optional[float] = None
    credit: Optional[float] = None
    balance: Optional[float] = None
    source_page: Optional[int] = None
    category: str = "Uncategorized"
    classification_method: str = "unclassified"
    confidence: Optional[float] = None
    review_status: str = "pending"
    validation_flags: list[str] = Field(default_factory=list)
    ocr_confidence: Optional[float] = None

class TransactionResponse(TransactionBase):
    id: str
    statement_id: str
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True

class TransactionUpdate(BaseModel):
    category: Optional[str] = None
    review_status: Optional[str] = None
    description: Optional[str] = None
    date: Optional[str] = None
    debit: Optional[float] = None
    credit: Optional[float] = None
    balance: Optional[float] = None

class TransactionListResponse(BaseModel):
    transactions: list[TransactionResponse]
    total: int
    page: int
    page_size: int
    total_pages: int


# ── Dashboard ──────────────────────────────────────────
class KPIData(BaseModel):
    total_transactions: int = 0
    total_credits: float = 0.0
    total_debits: float = 0.0
    uncategorized: int = 0
    needing_review: int = 0
    net_change: float = 0.0

class CategoryBreakdown(BaseModel):
    category: str
    total: float
    count: int
    percentage: float

class MonthlyTrend(BaseModel):
    month: str
    credits: float
    debits: float

class DashboardResponse(BaseModel):
    has_data: bool = False
    kpis: KPIData = Field(default_factory=KPIData)
    spending_by_category: list[CategoryBreakdown] = Field(default_factory=list)
    monthly_trends: list[MonthlyTrend] = Field(default_factory=list)
    recent_transactions: list[TransactionResponse] = Field(default_factory=list)
    statements: list[StatementResponse] = Field(default_factory=list)
    account_info: Optional[dict] = None
    validation_summary: Optional[dict] = None


# ── Classification ─────────────────────────────────────
class RuleBase(BaseModel):
    category: str
    rule_type: str = "keyword"  # keyword, regex
    pattern: str
    priority: int = 50
    is_active: bool = True

class RuleResponse(RuleBase):
    id: str
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True

class RuleCreate(RuleBase):
    pass

class RuleUpdate(BaseModel):
    category: Optional[str] = None
    rule_type: Optional[str] = None
    pattern: Optional[str] = None
    priority: Optional[int] = None
    is_active: Optional[bool] = None

class RulesListResponse(BaseModel):
    rules: list[RuleResponse]
    total: int


# ── Model Metrics ──────────────────────────────────────
class ModelMetricsResponse(BaseModel):
    version: str
    is_active: bool
    is_synthetic: bool = False
    training_samples: int
    accuracy: Optional[float] = None
    precision_macro: Optional[float] = None
    recall_macro: Optional[float] = None
    f1_macro: Optional[float] = None
    confusion_matrix: Optional[dict] = None
    classification_report: Optional[dict] = None
    created_at: datetime


# ── Validation ─────────────────────────────────────────
class ValidationFlag(BaseModel):
    transaction_id: str
    flag_type: str
    message: str
    severity: str  # warning, error, info

class ValidationSummary(BaseModel):
    total_transactions: int
    flagged_count: int
    balance_reconciled: bool
    balance_discrepancy: Optional[float] = None
    flags: list[ValidationFlag]


# ── Analytics ──────────────────────────────────────────
class AnalyticsResponse(BaseModel):
    spending_by_category: list[CategoryBreakdown]
    income_vs_expenditure: dict
    monthly_trends: list[MonthlyTrend]
    top_merchants: list[dict]
    debit_vs_credit: dict
    classification_coverage: dict


# ── Export ─────────────────────────────────────────────
class ExportRequest(BaseModel):
    format: str = "excel"  # excel, csv
    include_transactions: bool = True
    include_account_summary: bool = True
    include_category_summary: bool = True
    include_validation_report: bool = True


# ── Health ─────────────────────────────────────────────
class HealthResponse(BaseModel):
    status: str = "healthy"
    version: str = "1.0.0"
    tesseract_available: bool = False
    poppler_available: bool = False
    ml_model_loaded: bool = False
    database_connected: bool = False

