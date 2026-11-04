import axios from 'axios'
import type {
  Statement, StatementStatus, Transaction, TransactionListResponse,
  TransactionUpdate, DashboardResponse, Rule, RuleCreate,
  ModelMetrics, AnalyticsData, ValidationSummary, HealthResponse
} from '../types'

const api = axios.create({
  baseURL: '/api',
  headers: { 'Content-Type': 'application/json' },
  timeout: 30000,
})

// â”€â”€ Statements â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€

export async function uploadStatement(
  file: File,
  password?: string,
  onProgress?: (pct: number) => void,
): Promise<Statement> {
  const form = new FormData()
  form.append('file', file)
  if (password) form.append('password', password)

  const res = await api.post<Statement>('/statements/upload', form, {
    headers: { 'Content-Type': 'multipart/form-data' },
    onUploadProgress: (e) => {
      if (onProgress && e.total) {
        onProgress(Math.round((e.loaded / e.total) * 100))
      }
    },
  })
  return res.data
}

export async function getStatements(): Promise<Statement[]> {
  const res = await api.get<Statement[]>('/statements')
  return res.data
}

export async function getStatement(id: string): Promise<Statement> {
  const res = await api.get<Statement>(`/statements/${id}`)
  return res.data
}

export async function getStatementStatus(id: string): Promise<StatementStatus> {
  const res = await api.get<StatementStatus>(`/statements/${id}/status`)
  return res.data
}

export async function deleteStatement(id: string): Promise<void> {
  await api.delete(`/statements/${id}`)
}

export async function purgeAllData(): Promise<{ message: string }> {
  const res = await api.post<{ message: string }>('/statements/purge')
  return res.data
}

// â”€â”€ Transactions â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€

export interface TransactionFilters {
  page?: number
  page_size?: number
  search?: string
  category?: string
  date_from?: string
  date_to?: string
  classification_method?: string
  review_status?: string
  sort_by?: string
  sort_order?: 'asc' | 'desc'
}

export async function getTransactions(
  statementId: string,
  filters: TransactionFilters = {},
): Promise<TransactionListResponse> {
  const res = await api.get<TransactionListResponse>(
    `/statements/${statementId}/transactions`,
    { params: filters }
  )
  return res.data
}

export async function updateTransaction(
  statementId: string,
  transactionId: string,
  update: TransactionUpdate,
): Promise<Transaction> {
  const res = await api.put<Transaction>(
    `/statements/${statementId}/transactions/${transactionId}`,
    update,
  )
  return res.data
}


export async function deleteTransaction(statementId: string, transactionId: string): Promise<void> {
  await api.delete(`/statements/${statementId}/transactions/${transactionId}`)
}
export async function classifyStatement(id: string): Promise<{ message: string }> {
  const res = await api.post<{ message: string }>(`/statements/${id}/classify`)
  return res.data
}

// â”€â”€ Validation â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€

export async function getValidation(id: string): Promise<ValidationSummary> {
  const res = await api.get<ValidationSummary>(`/statements/${id}/validation`)
  return res.data
}

// â”€â”€ Analytics â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€

export async function getAnalytics(id: string): Promise<AnalyticsData> {
  const res = await api.get<AnalyticsData>(`/statements/${id}/analytics`)
  return res.data
}

// â”€â”€ Dashboard â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€

export async function getDashboard(): Promise<DashboardResponse> {
  const res = await api.get<DashboardResponse>('/dashboard')
  return res.data
}

// â”€â”€ Export â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€

export async function exportExcel(id: string): Promise<Blob> {
  const res = await api.get(`/statements/${id}/export/excel`, {
    responseType: 'blob',
  })
  return res.data
}

export async function exportCSV(id: string): Promise<Blob> {
  const res = await api.get(`/statements/${id}/export/csv`, {
    responseType: 'blob',
  })
  return res.data
}

export function downloadBlob(blob: Blob, filename: string) {
  const url = URL.createObjectURL(blob)
  const a = document.createElement('a')
  a.href = url
  a.download = filename
  document.body.appendChild(a)
  a.click()
  document.body.removeChild(a)
  URL.revokeObjectURL(url)
}

// â”€â”€ Rules â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€

export async function getRules(): Promise<Rule[]> {
  const res = await api.get<{ rules: Rule[]; total: number }>('/rules')
  return res.data.rules
}

export async function createRule(rule: RuleCreate): Promise<Rule> {
  const res = await api.post<Rule>('/rules', rule)
  return res.data
}

export async function updateRule(id: string, update: Partial<RuleCreate>): Promise<Rule> {
  const res = await api.put<Rule>(`/rules/${id}`, update)
  return res.data
}

export async function deleteRule(id: string): Promise<void> {
  await api.delete(`/rules/${id}`)
}

// â”€â”€ Model â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€

export async function getModelMetrics(): Promise<ModelMetrics> {
  const res = await api.get<ModelMetrics>('/model/metrics')
  return res.data
}

export async function retrainModel(): Promise<ModelMetrics> {
  const res = await api.post<ModelMetrics>('/model/retrain')
  return res.data
}

// â”€â”€ Health â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€

export async function getHealth(): Promise<HealthResponse> {
  const res = await api.get<HealthResponse>('/health')
  return res.data
}

// ── Settings ───────────────────────────────────────────────────────────────

export interface SystemSettingsConfig {
  retention_enabled: boolean
  confidence_threshold: number
}

export async function getSettings(): Promise<SystemSettingsConfig> {
  const res = await api.get<SystemSettingsConfig>('/settings')
  return res.data
}

export async function updateSettings(
  update: Partial<SystemSettingsConfig>,
): Promise<SystemSettingsConfig> {
  const res = await api.post<SystemSettingsConfig>('/settings', update)
  return res.data
}

export default api


