// All TypeScript types matching backend Pydantic schemas

export interface PageTypeInfo {
  page: number
  type: 'text' | 'scanned'
  char_count?: number
}

export interface Statement {
  id: string
  original_filename: string
  file_size?: number
  page_count?: number
  pdf_type?: 'text_based' | 'scanned' | 'mixed'
  status: 'uploaded' | 'detecting' | 'extracting' | 'standardizing' | 'classifying' | 'validating' | 'saving' | 'completed' | 'failed'
  processing_progress: number
  processing_message: string
  error_message?: string
  page_types?: PageTypeInfo[]
  password_protected?: boolean
  account_holder?: string
  bank_name?: string
  account_number_masked?: string
  ifsc_code?: string
  branch?: string
  statement_period_start?: string
  statement_period_end?: string
  opening_balance?: number
  closing_balance?: number
  created_at: string
  completed_at?: string
}

export interface StatementStatus {
  id: string
  status: Statement['status']
  processing_progress: number
  processing_message: string
  error_message?: string
  pdf_type?: string
  page_types?: PageTypeInfo[]
  page_count?: number
}

export interface Transaction {
  id: string
  statement_id: string
  date?: string
  description?: string
  original_description?: string
  debit?: number
  credit?: number
  balance?: number
  source_page?: number
  category: string
  classification_method: 'rule_based' | 'machine_learning' | 'manual' | 'unclassified'
  confidence?: number
  review_status: 'pending' | 'reviewed' | 'review_required'
  validation_flags: string[]
  ocr_confidence?: number
  created_at: string
  updated_at: string
}

export interface TransactionListResponse {
  transactions: Transaction[]
  total: number
  page: number
  page_size: number
  total_pages: number
}

export interface TransactionUpdate {
  category?: string
  review_status?: string
  description?: string
  date?: string
  debit?: number
  credit?: number
  balance?: number
}

export interface KPIData {
  total_transactions: number
  total_credits: number
  total_debits: number
  uncategorized: number
  needing_review: number
  net_change: number
}

export interface CategoryBreakdown {
  category: string
  total: number
  count: number
  percentage: number
}

export interface MonthlyTrend {
  month: string
  credits: number
  debits: number
}

export interface DashboardResponse {
  has_data: boolean
  kpis: KPIData
  spending_by_category: CategoryBreakdown[]
  monthly_trends: MonthlyTrend[]
  recent_transactions: Transaction[]
  statements: Statement[]
  account_info?: {
    account_holder?: string
    bank_name?: string
    account_number_masked?: string
    ifsc_code?: string
    branch?: string
    statement_period_start?: string
    statement_period_end?: string
    opening_balance?: number
    closing_balance?: number
  }
  validation_summary?: ValidationSummary
}

export interface ValidationFlag {
  transaction_id: string
  flag_type: string
  message: string
  severity: 'error' | 'warning' | 'info'
}

export interface ValidationSummary {
  total_transactions: number
  flagged_count: number
  balance_reconciled: boolean
  balance_discrepancy?: number
  flags: ValidationFlag[]
}

export interface Rule {
  id: string
  category: string
  rule_type: 'keyword' | 'regex'
  pattern: string
  priority: number
  is_active: boolean
  created_at: string
  updated_at: string
}

export interface RuleCreate {
  category: string
  rule_type: 'keyword' | 'regex'
  pattern: string
  priority: number
  is_active: boolean
}

export interface ModelMetrics {
  version: string
  is_active: boolean
  is_synthetic: boolean
  training_samples: number
  accuracy?: number
  precision_macro?: number
  recall_macro?: number
  f1_macro?: number
  confusion_matrix?: {
    labels: string[]
    matrix: number[][]
  }
  classification_report?: Record<string, Record<string, number>>
  created_at: string
}

export interface AnalyticsData {
  spending_by_category: CategoryBreakdown[]
  monthly_trends: MonthlyTrend[]
  top_merchants: Array<{ merchant: string; total: number }>
  classification_coverage: {
    total: number
    categorized: number
    rule_based: number
    ml_based: number
    manual: number
    unclassified: number
    needing_review: number
    coverage_pct: number
  }
  income_vs_expenditure: {
    total_income: number
    total_expenditure: number
    net: number
  }
  debit_vs_credit: {
    debits: number
    credits: number
  }
}

export interface HealthResponse {
  status: string
  version: string
  tesseract_available: boolean
  poppler_available: boolean
  ml_model_loaded: boolean
  database_connected: boolean
}

export type Page = 'dashboard' | 'upload' | 'transactions' | 'classification' | 'reports' | 'settings'

