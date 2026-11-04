import React, { useEffect, useState } from 'react'
import {
  ArrowDownLeft, ArrowUpRight, Wallet, ArrowLeftRight,
  AlertCircle, Download, Upload, CheckCircle2, XCircle, Building,
} from 'lucide-react'
import type { DashboardResponse, Page, Statement, Transaction, AnalyticsData, TransactionUpdate } from '../types'
import { getDashboard, getStatements, getAnalytics, updateTransaction, deleteTransaction } from '../api/client'
import { Button } from '../components/ui/Button'
import { StatCard } from '../components/ui/StatCard'
import { Badge } from '../components/ui/Badge'
import { EmptyState } from '../components/ui/EmptyState'
import { DonutChart } from '../components/charts/DonutChart'
import { TrendChart } from '../components/charts/TrendChart'
import { TransactionTable } from '../components/TransactionTable'
import { ExportModal } from '../components/ExportModal'
import { ReviewDrawer } from '../components/ReviewDrawer'
import { formatINR } from '../utils/format'

interface DashboardPageProps { setPage: (p: Page) => void }

export function Dashboard({ setPage }: DashboardPageProps) {
  const [allStatements, setAllStatements] = useState<Statement[]>([])
  const [selectedId, setSelectedId] = useState<string>('')
  const [data, setData] = useState<DashboardResponse | null>(null)
  const [analytics, setAnalytics] = useState<AnalyticsData | null>(null)
  const [loading, setLoading] = useState(true)
  const [exportOpen, setExportOpen] = useState(false)
  const [selectedTxn, setSelectedTxn] = useState<Transaction | null>(null)

  useEffect(() => {
    async function init() {
      try {
        setLoading(true)
        const [dashRes, stmtsRes] = await Promise.all([getDashboard(), getStatements()])
        setData(dashRes)
        const completed = stmtsRes.filter((s) => s.status === 'completed')
        setAllStatements(completed)
        if (completed.length > 0) setSelectedId(completed[0].id)
      } catch (err) { console.error('Failed to load dashboard', err) }
      finally { setLoading(false) }
    }
    init()
  }, [])

  useEffect(() => {
    if (!selectedId) return
    async function loadAnalytics() {
      try {
        setLoading(true)
        const res = await getAnalytics(selectedId)
        setAnalytics(res)
      } catch (err) { console.error('Failed to load analytics', err) }
      finally { setLoading(false) }
    }
    loadAnalytics()
  }, [selectedId])

  const handleUpdateCategory = async (txnId: string, update: TransactionUpdate) => {
    if (!selectedTxn) return
    await updateTransaction(selectedTxn.statement_id, txnId, update)
    const res = await getAnalytics(selectedId)
    setAnalytics(res)
  }

  const handleDelete = async (txnId: string) => {
    if (!selectedTxn) return
    await deleteTransaction(selectedTxn.statement_id, txnId)
    setSelectedTxn(null)
    const res = await getAnalytics(selectedId)
    setAnalytics(res)
  }

  if (loading && !data) return (
    <div className='page' style={{ textAlign: 'center', paddingTop: 100 }}>
      <span className='pulse-dot' style={{ display: 'inline-block', marginBottom: 12 }} />
      <p style={{ color: 'var(--muted)', fontSize: 13 }}>Loading financial telemetry...</p>
    </div>
  )

  if (!data || !data.has_data) return (
    <div className='page dashboard-page'>
      <EmptyState title='No Statements Processed'
        description='Upload your real bank statement PDF to automatically detect page types, extract account details, parse transactions, and classify spending.'
        onAction={() => setPage('upload')} actionLabel='Upload Bank Statement' />
    </div>
  )

  const selectedStmt = allStatements.find((s) => s.id === selectedId) ?? allStatements[0]
  const spendingByCategory = analytics?.spending_by_category ?? data.spending_by_category
  const monthlyTrends = analytics?.monthly_trends ?? data.monthly_trends
  const totalCredits = analytics?.income_vs_expenditure.total_income ?? data.kpis.total_credits
  const totalDebits = analytics?.income_vs_expenditure.total_expenditure ?? data.kpis.total_debits
  const netChange = analytics?.income_vs_expenditure.net ?? data.kpis.net_change
  const totalTxns = analytics?.classification_coverage.total ?? data.kpis.total_transactions
  const needingReview = analytics?.classification_coverage.needing_review ?? data.kpis.needing_review
  const isReconciled = !!(selectedStmt?.opening_balance != null && selectedStmt?.closing_balance != null)
  const recentTxns = data.recent_transactions.filter((t) => !selectedId || t.statement_id === selectedId)

  return (
    <div className='page dashboard-page'>
      <div className='dashboard-toolbar'>
        <div className='statement-select'>
          <span>ACTIVE STATEMENT</span>
          <select value={selectedId} onChange={(e) => setSelectedId(e.target.value)}>
            {allStatements.map((s) => (
              <option key={s.id} value={s.id}>{s.bank_name || 'Bank'}  —  {s.original_filename}</option>
            ))}
          </select>
        </div>
        <div style={{ display: 'flex', gap: 8 }}>
          {selectedStmt && (
            <Button variant='secondary' icon={<Download size={15} />} onClick={() => setExportOpen(true)}>Export Data</Button>
          )}
          <Button icon={<Upload size={15} />} onClick={() => setPage('upload')}>Upload Statement</Button>
        </div>
      </div>

      <div className={`validation-banner ${isReconciled ? '' : 'error'}`}>
        <div className='validation-icon'>
          {isReconciled ? <CheckCircle2 size={18} /> : <XCircle size={18} />}
        </div>
        <div>
          <strong>{isReconciled ? 'Balance Reconciled' : 'Discrepancy Detected'}</strong>
          <span>{isReconciled ? 'Opening balance + deposits \u2212 withdrawals matches closing balance.' : 'Extraction flags suggest reviewing specific transaction values or OCR confidence.'}</span>
        </div>
        <Badge tone={isReconciled ? 'green' : 'red'}>{isReconciled ? 'Reconciled 100%' : 'Needs Review'}</Badge>
      </div>

      {selectedStmt && (
        <section className='account-card'>
          <div className='account-bank'>
            <div className='bank-logo'><Building size={22} color='#4444db' /></div>
            <div>
              <span>VERIFIED ACCOUNT</span>
              <h3>{selectedStmt.bank_name || 'Bank Statement'}</h3>
              <p>{selectedStmt.account_holder || 'Authorized Account Holder'}</p>
            </div>
          </div>
          <div className='account-details'>
            <div><span>Account Number</span><strong>{selectedStmt.account_number_masked || '\u2022\u2022\u2022\u2022 \u2022\u2022\u2022\u2022'}</strong></div>
            <div><span>IFSC Code</span><strong>{selectedStmt.ifsc_code || '\u2014'}</strong></div>
            <div><span>Period</span><strong>{selectedStmt.statement_period_start && selectedStmt.statement_period_end ? selectedStmt.statement_period_start + ' to ' + selectedStmt.statement_period_end : 'Full Period'}</strong></div>
            <div><span>Opening Balance</span><strong>{formatINR(selectedStmt.opening_balance)}</strong></div>
            <div><span>Closing Balance</span><strong>{formatINR(selectedStmt.closing_balance)}</strong></div>
          </div>
        </section>
      )}

      <div className='stats-grid'>
        <StatCard label='Total Credits' value={formatINR(totalCredits)} icon={<ArrowDownLeft size={18} />} tone='teal' />
        <StatCard label='Total Debits' value={formatINR(totalDebits)} icon={<ArrowUpRight size={18} />} tone='indigo' />
        <StatCard label='Net Flow' value={formatINR(netChange)} icon={<Wallet size={18} />} tone='blue' />
        <StatCard label='Transactions' value={totalTxns.toLocaleString()} icon={<ArrowLeftRight size={18} />} tone='purple' />
        <StatCard label='Needs Review' value={needingReview.toString()} icon={<AlertCircle size={18} />} tone={needingReview > 0 ? 'amber' : 'teal'} />
      </div>

      <div className='charts-grid'>
        <section className='card chart-card'>
          <div className='card-head'><div><h3>Spend Distribution</h3><p>Categorized expenditures by volume</p></div></div>
          <DonutChart data={spendingByCategory} />
        </section>
        <section className='card chart-card'>
          <div className='card-head'><div><h3>Cash Flow Trend</h3><p>Monthly credits and debits trajectory</p></div></div>
          <TrendChart data={monthlyTrends} />
        </section>
      </div>

      <section className='card recent-card'>
        <div className='card-head' style={{ padding: '16px 19px' }}>
          <div><h3>Recent Statement Entries</h3><p>Directly extracted transactions</p></div>
          <button className='text-button' onClick={() => setPage('transactions')}>View all ({totalTxns})</button>
        </div>
        <TransactionTable transactions={recentTxns.slice(0, 5)} compact onSelectTransaction={(t) => setSelectedTxn(t)} />
      </section>

      {exportOpen && selectedStmt && (
        <ExportModal statementId={selectedStmt.id} statementFilename={selectedStmt.original_filename} onClose={() => setExportOpen(false)} />
      )}
      {selectedTxn && (
        <ReviewDrawer transaction={selectedTxn} onClose={() => setSelectedTxn(null)} onSave={handleUpdateCategory} onDelete={handleDelete} />
      )}
    </div>
  )
}


