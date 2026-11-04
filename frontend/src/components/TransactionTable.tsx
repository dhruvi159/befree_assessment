import React from 'react'
import { AlertCircle, ChevronRight, Edit2 } from 'lucide-react'
import type { Transaction } from '../types'
import {
  formatDate,
  formatINR,
  getCategoryColor,
  methodLabel,
  methodTone,
} from '../utils/format'
import { Badge } from './ui/Badge'

interface TransactionTableProps {
  transactions: Transaction[]
  compact?: boolean
  onSelectTransaction?: (t: Transaction) => void
}

export function TransactionTable({
  transactions,
  compact = false,
  onSelectTransaction,
}: TransactionTableProps) {
  if (!transactions || transactions.length === 0) {
    return (
      <div style={{ padding: '32px', textAlign: 'center', color: '#6d7588', fontSize: 13 }}>
        No transactions found.
      </div>
    )
  }

  return (
    <div className="table-scroll">
      <table className={`transaction-table ${compact ? 'compact' : ''}`}>
        <thead>
          <tr>
            <th>Date</th>
            <th>Description</th>
            <th>Debit</th>
            <th>Credit</th>
            {!compact && <th>Balance</th>}
            <th>Category</th>
            {!compact && <th>Method</th>}
            {!compact && <th>Confidence</th>}
            {!compact && <th>Review Status</th>}
            <th />
          </tr>
        </thead>
        <tbody>
          {transactions.map((t) => {
            const isFlagged = t.validation_flags && t.validation_flags.length > 0
            const tone = getCategoryColor(t.category)
            const confPct = t.confidence !== null && t.confidence !== undefined ? Math.round(t.confidence * 100) : null

            return (
              <tr
                key={t.id}
                className={isFlagged ? 'flagged-row' : ''}
                style={{ cursor: onSelectTransaction ? 'pointer' : 'default' }}
                onClick={() => onSelectTransaction?.(t)}
              >
                <td>{formatDate(t.date)}</td>
                <td className="description">
                  <span title={t.original_description || t.description}>
                    {t.description || t.original_description || '—'}
                  </span>
                  {isFlagged && (
                    <small title={t.validation_flags.join(', ')}>
                      <AlertCircle size={11} /> {t.validation_flags[0].replace(/_/g, ' ')}
                    </small>
                  )}
                </td>
                <td className="amount debit">{t.debit ? formatINR(t.debit) : '—'}</td>
                <td className="amount credit">{t.credit ? formatINR(t.credit) : '—'}</td>
                {!compact && (
                  <td className="amount">{t.balance !== null && t.balance !== undefined ? formatINR(t.balance) : '—'}</td>
                )}
                <td>
                  <span className={`category-chip ${tone}`}>
                    {t.category}
                  </span>
                </td>
                {!compact && (
                  <td>
                    <Badge tone={methodTone(t.classification_method)}>
                      {methodLabel(t.classification_method)}
                    </Badge>
                  </td>
                )}
                {!compact && (
                  <td>
                    {confPct !== null ? (
                      <div className="confidence">
                        <div>
                          <i
                            style={{ width: `${confPct}%` }}
                            className={confPct < 75 ? 'low' : ''}
                          />
                        </div>
                        <span>{confPct}%</span>
                      </div>
                    ) : (
                      <span style={{ color: '#a0a6b4', fontSize: 10 }}>—</span>
                    )}
                  </td>
                )}
                {!compact && (
                  <td>
                    <Badge
                      tone={
                        t.review_status === 'reviewed'
                          ? 'green'
                          : t.review_status === 'review_required'
                          ? 'amber'
                          : 'neutral'
                      }
                    >
                      {t.review_status === 'review_required'
                        ? 'Needs Review'
                        : t.review_status === 'reviewed'
                        ? 'Reviewed'
                        : 'Pending'}
                    </Badge>
                  </td>
                )}
                <td>
                  {onSelectTransaction && (
                    <button
                      className="icon-button"
                      onClick={(e) => {
                        e.stopPropagation()
                        onSelectTransaction(t)
                      }}
                      title="Edit / Review"
                    >
                      <Edit2 size={14} />
                    </button>
                  )}
                </td>
              </tr>
            )
          })}
        </tbody>
      </table>
    </div>
  )
}

