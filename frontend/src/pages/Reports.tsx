import React, { useEffect, useState } from 'react'
import {
  BarChart3,
  TrendingUp,
  Store,
  DollarSign,
  Download,
} from 'lucide-react'
import type { AnalyticsData, Page, Statement } from '../types'
import { getAnalytics, getStatements } from '../api/client'
import { Button } from '../components/ui/Button'
import { EmptyState } from '../components/ui/EmptyState'
import { DonutChart } from '../components/charts/DonutChart'
import { TrendChart } from '../components/charts/TrendChart'
import { ExportModal } from '../components/ExportModal'
import { formatINR } from '../utils/format'

interface ReportsPageProps {
  setPage: (p: Page) => void
}

export function Reports({ setPage }: ReportsPageProps) {
  const [statements, setStatements] = useState<Statement[]>([])
  const [selectedStatementId, setSelectedStatementId] = useState<string>('')
  const [analytics, setAnalytics] = useState<AnalyticsData | null>(null)
  const [loading, setLoading] = useState(true)
  const [exportOpen, setExportOpen] = useState(false)

  useEffect(() => {
    async function init() {
      try {
        setLoading(true)
        const stmts = await getStatements()
        setStatements(stmts)
        const completed = stmts.filter((s) => s.status === 'completed')
        if (completed.length > 0) {
          setSelectedStatementId(completed[0].id)
        }
      } catch (err) {
        console.error('Error fetching statements', err)
      } finally {
        setLoading(false)
      }
    }
    init()
  }, [])

  useEffect(() => {
    if (!selectedStatementId) return
    async function load() {
      try {
        setLoading(true)
        const res = await getAnalytics(selectedStatementId)
        setAnalytics(res)
      } catch (err) {
        console.error('Error fetching analytics', err)
      } finally {
        setLoading(false)
      }
    }
    load()
  }, [selectedStatementId])

  const currentStatement = statements.find((s) => s.id === selectedStatementId)

  if (!loading && statements.length === 0) {
    return (
      <div className="page" style={{ paddingTop: 28 }}>
        <EmptyState
          title="No Analytics Available"
          description="Upload your real bank statement PDF to view categorized spending reports, income trends, and merchant breakdowns."
          onAction={() => setPage('upload')}
          actionLabel="Upload Bank Statement"
        />
      </div>
    )
  }

  return (
    <div className="page" style={{ paddingTop: 28 }}>
      {/* Header Selector */}
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 20 }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: 10 }}>
          <span style={{ fontSize: 11, fontWeight: 700, color: 'var(--muted)' }}>SELECT STATEMENT:</span>
          <select
            className="filter-select"
            value={selectedStatementId}
            onChange={(e) => setSelectedStatementId(e.target.value)}
          >
            {statements.map((s) => (
              <option key={s.id} value={s.id}>
                {s.bank_name || 'Bank'} — {s.original_filename}
              </option>
            ))}
          </select>
        </div>

        {currentStatement && (
          <Button variant="secondary" icon={<Download size={14} />} onClick={() => setExportOpen(true)}>
            Export Reports
          </Button>
        )}
      </div>

      {analytics && (
        <>
          {/* Income vs Expenditure summary banner */}
          <div
            style={{
              display: 'grid',
              gridTemplateColumns: 'repeat(3, 1fr)',
              gap: 14,
              marginBottom: 20,
            }}
          >
            <div className="card" style={{ padding: '16px 20px' }}>
              <span style={{ fontSize: 11, color: 'var(--muted)' }}>Total Inflow (Credits)</span>
              <strong style={{ display: 'block', fontSize: 20, color: '#07825f', marginTop: 4 }}>
                {formatINR(analytics.income_vs_expenditure.total_income)}
              </strong>
            </div>

            <div className="card" style={{ padding: '16px 20px' }}>
              <span style={{ fontSize: 11, color: 'var(--muted)' }}>Total Outflow (Debits)</span>
              <strong style={{ display: 'block', fontSize: 20, color: '#ef5b5b', marginTop: 4 }}>
                {formatINR(analytics.income_vs_expenditure.total_expenditure)}
              </strong>
            </div>

            <div className="card" style={{ padding: '16px 20px' }}>
              <span style={{ fontSize: 11, color: 'var(--muted)' }}>Net Period Savings</span>
              <strong
                style={{
                  display: 'block',
                  fontSize: 20,
                  color: analytics.income_vs_expenditure.net >= 0 ? '#4444db' : '#ef5b5b',
                  marginTop: 4,
                }}
              >
                {formatINR(analytics.income_vs_expenditure.net)}
              </strong>
            </div>
          </div>

          {/* Charts Row */}
          <div className="charts-grid" style={{ marginBottom: 20 }}>
            <section className="card chart-card">
              <div className="card-head">
                <div>
                  <h3>Spend by Category</h3>
                  <p>Distribution of expenditures</p>
                </div>
              </div>
              <DonutChart data={analytics.spending_by_category} />
            </section>

            <section className="card chart-card">
              <div className="card-head">
                <div>
                  <h3>Monthly Income vs Expenses</h3>
                  <p>Inflows (green) versus Outflows (red)</p>
                </div>
              </div>
              <TrendChart data={analytics.monthly_trends} />
            </section>
          </div>

          {/* Top Merchants Table */}
          <section className="card" style={{ padding: '18px 22px' }}>
            <div className="card-head" style={{ marginBottom: 14 }}>
              <div>
                <h3>Identified Top Counterparties & Merchants</h3>
                <p>Aggregate spend grouped by identified merchant / beneficiary</p>
              </div>
              <Store size={18} color="var(--muted)" />
            </div>

            <div className="table-scroll">
              <table className="transaction-table compact">
                <thead>
                  <tr>
                    <th>Merchant / Counterparty</th>
                    <th>Total Debited (₹)</th>
                  </tr>
                </thead>
                <tbody>
                  {analytics.top_merchants.map((m, i) => (
                    <tr key={i}>
                      <td>
                        <strong>{m.merchant}</strong>
                      </td>
                      <td className="amount debit">{formatINR(m.total)}</td>
                    </tr>
                  ))}
                  {analytics.top_merchants.length === 0 && (
                    <tr>
                      <td colSpan={2} style={{ textAlign: 'center', color: 'var(--muted)', padding: 24 }}>
                        No merchants identified yet.
                      </td>
                    </tr>
                  )}
                </tbody>
              </table>
            </div>
          </section>
        </>
      )}

      {exportOpen && currentStatement && (
        <ExportModal
          statementId={currentStatement.id}
          statementFilename={currentStatement.original_filename}
          onClose={() => setExportOpen(false)}
        />
      )}
    </div>
  )
}

