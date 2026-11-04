import React, { useEffect, useState } from 'react'
import {
  Search,
  Filter,
  Download,
  AlertTriangle,
  RotateCcw,
  Sparkles,
  ChevronLeft,
  ChevronRight,
} from 'lucide-react'
import type { Page, Statement, Transaction, TransactionUpdate } from '../types'
import {
  getStatements,
  getTransactions,
  updateTransaction,
  classifyStatement,
} from '../api/client'
import { Button } from '../components/ui/Button'
import { EmptyState } from '../components/ui/EmptyState'
import { TransactionTable } from '../components/TransactionTable'
import { ReviewDrawer } from '../components/ReviewDrawer'
import { ExportModal } from '../components/ExportModal'

interface TransactionsPageProps {
  setPage: (p: Page) => void
}

const CATEGORIES = [
  'All Categories',
  'Food & Dining',
  'Transportation',
  'Shopping',
  'Entertainment',
  'Utilities',
  'Rent & Housing',
  'Healthcare',
  'Education',
  'Salary & Income',
  'Transfers',
  'Cash Withdrawal',
  'Cash Deposit',
  'Investments',
  'Banking Charges',
  'Insurance',
  'Taxes',
  'Interest',
  'Refunds & Reversals',
  'Uncategorized',
]

export function Transactions({ setPage }: TransactionsPageProps) {
  const [statements, setStatements] = useState<Statement[]>([])
  const [selectedStatementId, setSelectedStatementId] = useState<string>('')
  const [transactions, setTransactions] = useState<Transaction[]>([])
  const [total, setTotal] = useState(0)
  const [page, setCurrentPage] = useState(1)
  const [pageSize] = useState(50)
  const [search, setSearch] = useState('')
  const [category, setCategory] = useState('All Categories')
  const [reviewStatus, setReviewStatus] = useState<string>('all')
  const [flaggedOnly, setFlaggedOnly] = useState(false)
  const [loading, setLoading] = useState(true)
  const [selectedTxn, setSelectedTxn] = useState<Transaction | null>(null)
  const [exportOpen, setExportOpen] = useState(false)
  const [reclassifying, setReclassifying] = useState(false)

  // 1. Load statements
  useEffect(() => {
    async function loadStatements() {
      try {
        setLoading(true)
        const stmts = await getStatements()
        setStatements(stmts)
        const completed = stmts.filter((s) => s.status === 'completed')
        if (completed.length > 0) {
          setSelectedStatementId(completed[0].id)
        }
      } catch (err) {
        console.error('Error loading statements', err)
      } finally {
        setLoading(false)
      }
    }
    loadStatements()
  }, [])

  // 2. Load transactions when statement, filters, or page changes
  useEffect(() => {
    if (!selectedStatementId) return
    loadTransactions()
  }, [selectedStatementId, page, search, category, reviewStatus, flaggedOnly])

  const loadTransactions = async () => {
    if (!selectedStatementId) return
    try {
      setLoading(true)
      const res = await getTransactions(selectedStatementId, {
        page,
        page_size: pageSize,
        search: search || undefined,
        category: category !== 'All Categories' ? category : undefined,
        review_status: reviewStatus !== 'all' ? reviewStatus : undefined,
      })
      let list = res.transactions
      if (flaggedOnly) {
        list = list.filter((t) => t.validation_flags && t.validation_flags.length > 0)
      }
      setTransactions(list)
      setTotal(res.total)
    } catch (err) {
      console.error('Error loading transactions', err)
    } finally {
      setLoading(false)
    }
  }

  const handleUpdate = async (txnId: string, update: TransactionUpdate) => {
    if (!selectedStatementId) return
    await updateTransaction(selectedStatementId, txnId, update)
    await loadTransactions()
  }

  const handleDelete = async (txnId: string) => {
    if (!selectedStatementId) return
    await deleteTransaction(selectedStatementId, txnId)
    setSelectedTxn(null)
    await loadTransactions()
  }

  const handleReclassify = async () => {
    if (!selectedStatementId) return
    try {
      setReclassifying(true)
      await classifyStatement(selectedStatementId)
      await loadTransactions()
    } finally {
      setReclassifying(false)
    }
  }

  const currentStatement = statements.find((s) => s.id === selectedStatementId)
  const totalPages = Math.ceil(total / pageSize) || 1
  const flaggedCount = transactions.filter((t) => t.validation_flags?.length > 0).length

  if (!loading && statements.length === 0) {
    return (
      <div className="page transactions-page">
        <EmptyState
          title="No Transactions to Display"
          description="Upload your real bank statement PDF to extract and review transactions."
          onAction={() => setPage('upload')}
          actionLabel="Upload Bank Statement"
        />
      </div>
    )
  }

  return (
    <div className="page transactions-page">
      {/* Flagged Banner */}
      {flaggedCount > 0 && (
        <div className="validation-mini">
          <AlertTriangle size={18} />
          <div>
            <strong>{flaggedCount} transactions require human review</strong>
            <span>
              Rows with low OCR confidence, ambiguous categorization, or reconciliation flags are highlighted.
            </span>
          </div>
          <button onClick={() => setFlaggedOnly(!flaggedOnly)}>
            {flaggedOnly ? 'Show All Entries' : 'Filter Flagged Only'}
          </button>
        </div>
      )}

      {/* Statement Selector & Actions */}
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 14 }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: 10 }}>
          <span style={{ fontSize: 11, fontWeight: 700, color: 'var(--muted)' }}>STATEMENT:</span>
          <select
            className="filter-select"
            value={selectedStatementId}
            onChange={(e) => {
              setSelectedStatementId(e.target.value)
              setCurrentPage(1)
            }}
          >
            {statements.map((s) => (
              <option key={s.id} value={s.id}>
                {s.bank_name || 'Bank'} â€” {s.original_filename}
              </option>
            ))}
          </select>
        </div>

        <div style={{ display: 'flex', gap: 8 }}>
          <Button
            variant="secondary"
            icon={<RotateCcw size={14} />}
            onClick={handleReclassify}
            disabled={reclassifying}
          >
            {reclassifying ? 'Reclassifying...' : 'Re-run Rules & ML'}
          </Button>
          <Button
            variant="secondary"
            icon={<Download size={14} />}
            onClick={() => setExportOpen(true)}
          >
            Export
          </Button>
        </div>
      </div>

      {/* Table Toolbar */}
      <div className="table-toolbar">
        <div className="search-box">
          <Search size={15} />
          <input
            type="text"
            placeholder="Search by narration, merchant, or amounts..."
            value={search}
            onChange={(e) => {
              setSearch(e.target.value)
              setCurrentPage(1)
            }}
          />
        </div>

        <select
          className="filter-select"
          value={category}
          onChange={(e) => {
            setCategory(e.target.value)
            setCurrentPage(1)
          }}
        >
          {CATEGORIES.map((c) => (
            <option key={c} value={c}>
              {c}
            </option>
          ))}
        </select>

        <select
          className="filter-select"
          value={reviewStatus}
          onChange={(e) => {
            setReviewStatus(e.target.value)
            setCurrentPage(1)
          }}
        >
          <option value="all">All Statuses</option>
          <option value="review_required">Needs Review</option>
          <option value="reviewed">Reviewed</option>
          <option value="pending">Pending</option>
        </select>

        <label className="flag-toggle">
          <input
            type="checkbox"
            checked={flaggedOnly}
            onChange={(e) => setFlaggedOnly(e.target.checked)}
          />
          <i /> Flagged only
        </label>
      </div>

      {/* Main Table Card */}
      <section className="card full-table">
        <div className="table-meta">
          <div>
            <b>{total.toLocaleString()} transactions found</b>
            <span> Â· Click any row to inspect, edit narration, or modify category</span>
          </div>
        </div>

        <TransactionTable
          transactions={transactions}
          onSelectTransaction={(t) => setSelectedTxn(t)}
        />

        {/* Pagination */}
        <div className="pagination">
          <span style={{ fontSize: 11, color: 'var(--muted)' }}>
            Page <strong style={{ color: 'var(--ink)' }}>{page}</strong> of{' '}
            <strong style={{ color: 'var(--ink)' }}>{totalPages}</strong>
            <span style={{ margin: '0 6px', opacity: 0.4 }}>·</span>
            {total} entries total
          </span>
          <div>
            <button
              disabled={page <= 1}
              onClick={() => setCurrentPage((p) => Math.max(1, p - 1))}
            >
              <ChevronLeft size={13} /> Previous
            </button>
            <span
              style={{
                display: 'inline-flex',
                alignItems: 'center',
                justifyContent: 'center',
                minWidth: 34,
                height: 34,
                borderRadius: 8,
                background: 'var(--primary)',
                color: 'white',
                fontSize: 11,
                fontWeight: 700,
                padding: '0 10px',
              }}
            >
              {page}
            </span>
            <button
              disabled={page >= totalPages}
              onClick={() => setCurrentPage((p) => Math.min(totalPages, p + 1))}
            >
              Next <ChevronRight size={13} />
            </button>
          </div>
        </div>
      </section>

      {/* Review Drawer */}
      {selectedTxn && (
        <ReviewDrawer
          transaction={selectedTxn}
          onClose={() => setSelectedTxn(null)}
          onSave={handleUpdate}
          onDelete={handleDelete}
        />
      )}

      {/* Export Modal */}
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



