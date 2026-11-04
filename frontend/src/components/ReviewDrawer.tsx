import React, { useState } from 'react'
import { X, Check, AlertTriangle, ShieldCheck, Trash2 } from 'lucide-react'
import type { Transaction, TransactionUpdate } from '../types'
import { Button } from './ui/Button'
import { Badge } from './ui/Badge'
import { formatINR } from '../utils/format'

interface ReviewDrawerProps {
  transaction: Transaction | null
  onClose: () => void
  onSave: (transactionId: string, update: TransactionUpdate) => Promise<void>
  onDelete?: (transactionId: string) => Promise<void>
}

const CATEGORIES = [
  'Food & Dining','Transportation','Shopping','Entertainment','Utilities',
  'Rent & Housing','Healthcare','Education','Salary & Income','Transfers',
  'Cash Withdrawal','Cash Deposit','Investments','Banking Charges','Insurance',
  'Taxes','Interest','Refunds & Reversals','Friends & Family','Uncategorized',
]

const inp: React.CSSProperties = {
  width: '100%', height: 38, border: '1px solid var(--line)', borderRadius: 8,
  padding: '0 10px', fontSize: 12, background: 'var(--surface)', color: 'var(--ink)', outline: 'none',
}

export function ReviewDrawer({ transaction, onClose, onSave, onDelete }: ReviewDrawerProps) {
  const [category, setCategory] = useState(transaction?.category || 'Uncategorized')
  const [description, setDescription] = useState(transaction?.description || '')
  const [date, setDate] = useState(transaction?.date || '')
  const [debit, setDebit] = useState<string>(transaction?.debit != null ? String(transaction.debit) : '')
  const [credit, setCredit] = useState<string>(transaction?.credit != null ? String(transaction.credit) : '')
  const [balance, setBalance] = useState<string>(transaction?.balance != null ? String(transaction.balance) : '')
  const [saving, setSaving] = useState(false)
  const [savedOk, setSavedOk] = useState(false)
  const [confirmDel, setConfirmDel] = useState(false)

  const handleSave = async () => {
    try {
      setSaving(true)
      await onSave(transaction.id, {
        category,
        review_status: 'reviewed',
        description: description || undefined,
        date: date || undefined,
        debit: debit !== '' ? parseFloat(debit) : undefined,
        credit: credit !== '' ? parseFloat(credit) : undefined,
        balance: balance !== '' ? parseFloat(balance) : undefined,
      })
      setSavedOk(true)
      setTimeout(() => onClose(), 600)
    } catch (e) { console.error(e) }
    finally { setSaving(false) }
  }

  const handleDelete = async () => {
    if (!onDelete) return
    try { setSaving(true); await onDelete(transaction.id); onClose() }
    catch (e) { console.error(e) }
    finally { setSaving(false) }
  }

  if (!transaction) return null

  const confPct = transaction.confidence ? Math.round(transaction.confidence * 100) : null

  return (
    <>
      <div className='overlay' onClick={onClose} />
      <aside className='drawer'>
        <div className='drawer-head'>
          <div>
            <Badge tone={transaction.validation_flags.length > 0 ? 'amber' : 'indigo'}>
              {transaction.validation_flags.length > 0 ? 'REVIEW NEEDED' : 'TRANSACTION DETAILS'}
            </Badge>
            <h2>Transaction Inspector</h2>
          </div>
          <button className='icon-button' onClick={onClose}><X size={18} /></button>
        </div>
        <div className='drawer-body'>
          {transaction.validation_flags.length > 0 && (
            <div className='match-card' style={{ background: '#fff9eb', borderColor: '#f2dfb7', marginBottom: 14 }}>
              <div className='match-head' style={{ color: '#9b620b' }}>
                <span style={{ display: 'flex', alignItems: 'center', gap: 4 }}>
                  <AlertTriangle size={13} /> VALIDATION WARNINGS
                </span>
              </div>
              <ul style={{ margin: '8px 0 0', paddingLeft: 16, fontSize: 11, color: '#8b672c' }}>
                {transaction.validation_flags.map((f) => <li key={f}>{f.replace(/_/g, ' ')}</li>)}
              </ul>
            </div>
          )}
          <div className='field-block'>
            <label>Date</label>
            <input type='date' style={inp} value={date} onChange={(e) => setDate(e.target.value)} />
          </div>
          <div className='field-block'>
            <label>Description / Narration</label>
            <input type='text' style={inp} value={description} onChange={(e) => setDescription(e.target.value)} placeholder='Transaction description' />
          </div>
          <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr 1fr', gap: 10 }}>
            <div className='field-block'>
              <label>Debit ({'\u20b9'})</label>
              <input type='number' min='0' step='0.01' style={inp} value={debit}
                onChange={(e) => { setDebit(e.target.value); if (e.target.value) setCredit('') }}
                placeholder='0.00' />
            </div>
            <div className='field-block'>
              <label>Credit ({'\u20b9'})</label>
              <input type='number' min='0' step='0.01' style={inp} value={credit}
                onChange={(e) => { setCredit(e.target.value); if (e.target.value) setDebit('') }}
                placeholder='0.00' />
            </div>
            <div className='field-block'>
              <label>Balance ({'\u20b9'})</label>
              <input type='number' min='0' step='0.01' style={inp} value={balance}
                onChange={(e) => setBalance(e.target.value)} placeholder='0.00' />
            </div>
          </div>
          <div className='field-block'>
            <label>Category</label>
            <select value={category} onChange={(e) => setCategory(e.target.value)} style={{ ...inp, height: 40 }}>
              {CATEGORIES.map((c) => <option key={c} value={c}>{c}</option>)}
            </select>
          </div>
          <div className='match-card'>
            <div className='match-head'>
              <span>CLASSIFICATION</span>
              <Badge tone='blue'>
                {transaction.classification_method === 'rule_based' ? 'Rule Match'
                  : transaction.classification_method === 'machine_learning' ? 'ML Predicted'
                  : transaction.classification_method === 'manual' ? 'Manual Verified' : 'Unclassified'}
              </Badge>
            </div>
            <p style={{ fontSize: 11, color: 'var(--muted)', margin: '8px 0 0' }}>Model score: {confPct !== null ? confPct + '%' : 'N/A'}</p>
          </div>
          <div style={{ padding: 12, borderRadius: 8, background: '#eef9f5', color: '#07825f', fontSize: 11, display: 'flex', gap: 8, alignItems: 'center' }}>
            <ShieldCheck size={18} /><span>All processing occurs strictly on-premise.</span>
          </div>
          {savedOk && <div className='save-toast'><Check size={14} /> Saved successfully</div>}
        </div>
        <div className='drawer-footer'>
          {onDelete && (
            confirmDel ? (
              <div style={{ display: 'flex', gap: 8 }}>
                <Button variant='secondary' onClick={() => setConfirmDel(false)} disabled={saving}>Cancel</Button>
                <Button onClick={handleDelete} disabled={saving} style={{ background: '#ef5b5b', borderColor: '#ef5b5b', color: 'white' }}>Confirm Delete</Button>
              </div>
            ) : (
              <button className='icon-button' style={{ color: '#ef5b5b', marginRight: 'auto' }} onClick={() => setConfirmDel(true)} title='Delete transaction'>
                <Trash2 size={16} />
              </button>
            )
          )}
          {!confirmDel && (
            <>
              <Button variant='secondary' onClick={onClose} disabled={saving}>Cancel</Button>
              <Button onClick={handleSave} disabled={saving}>{saving ? 'Saving...' : 'Save & Verify'}</Button>
            </>
          )}
        </div>
      </aside>
    </>
  )
}
