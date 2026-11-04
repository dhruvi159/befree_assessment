import React, { useEffect, useState } from 'react'
import {
  Plus,
  Trash2,
  ShieldCheck,
  CheckCircle2,
  Sliders,
  Database,
} from 'lucide-react'
import type { Page, Rule } from '../types'
import {
  getRules,
  createRule,
  deleteRule,
  getSettings,
  updateSettings,
  purgeAllData,
} from '../api/client'
import { Button } from '../components/ui/Button'
import { Badge } from '../components/ui/Badge'
import { Switch } from '../components/ui/Switch'

interface SettingsPageProps {
  setPage: (p: Page) => void
}

const CATEGORIES = [
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

export function Settings({ setPage }: SettingsPageProps) {
  const [rules, setRules] = useState<Rule[]>([])
  const [threshold, setThreshold] = useState<number>(() => {
    if (typeof window !== 'undefined') {
      const saved = localStorage.getItem('statementiq_confidence_threshold')
      if (saved) return Number(saved)
    }
    return 75
  })
  const [retention, setRetention] = useState<boolean>(() => {
    if (typeof window !== 'undefined') {
      return localStorage.getItem('statementiq_retention') === 'true'
    }
    return false
  })
  const [newCat, setNewCat] = useState('Food & Dining')
  const [newPattern, setNewPattern] = useState('')
  const [newType, setNewType] = useState<'keyword' | 'regex'>('keyword')
  const [newPriority, setNewPriority] = useState(80)
  const [addingRule, setAddingRule] = useState(false)
  const [savedMessage, setSavedMessage] = useState('')
  const [purging, setPurging] = useState(false)
  const [confirmPurge, setConfirmPurge] = useState(false)

  const loadData = async () => {
    try {
      const [r, s] = await Promise.allSettled([getRules(), getSettings()])
      if (r.status === 'fulfilled') setRules(r.value)
      if (s.status === 'fulfilled' && s.value) {
        const backendRetention = Boolean(s.value.retention_enabled)
        const backendThreshold = Math.round(s.value.confidence_threshold * 100)
        setRetention(backendRetention)
        setThreshold(backendThreshold)
        if (typeof window !== 'undefined') {
          localStorage.setItem('statementiq_retention', String(backendRetention))
          localStorage.setItem('statementiq_confidence_threshold', String(backendThreshold))
        }
      }
    } catch (err) {
      console.error('Error loading settings', err)
    }
  }

  const handlePurgeData = async () => {
    try {
      setPurging(true)
      await purgeAllData()
      setSavedMessage('All statement records and extracted transactions have been completely purged.')
      setConfirmPurge(false)
      setTimeout(() => setSavedMessage(''), 4000)
    } catch (err) {
      console.error('Failed to purge data', err)
      setSavedMessage('Failed to purge data. Please check backend connection.')
      setTimeout(() => setSavedMessage(''), 4000)
    } finally {
      setPurging(false)
    }
  }

  useEffect(() => {
    loadData()
  }, [])

  const handleToggleRetention = async (newVal: boolean) => {
    setRetention(newVal)
    if (typeof window !== 'undefined') {
      localStorage.setItem('statementiq_retention', String(newVal))
    }
    try {
      await updateSettings({ retention_enabled: newVal })
    } catch (e) {
      console.error('Failed to sync retention setting with backend', e)
    }
    setSavedMessage(
      newVal
        ? 'Auto-purge policy enabled (session retention active).'
        : 'Auto-purge policy disabled (persistent storage active).'
    )
    setTimeout(() => setSavedMessage(''), 3000)
  }

  const handleThresholdChange = async (newVal: number) => {
    setThreshold(newVal)
    if (typeof window !== 'undefined') {
      localStorage.setItem('statementiq_confidence_threshold', String(newVal))
    }
    try {
      await updateSettings({ confidence_threshold: newVal / 100.0 })
    } catch (e) {
      console.error('Failed to sync threshold with backend', e)
    }
  }

  const handleAddRule = async (e: React.FormEvent) => {
    e.preventDefault()
    if (!newPattern.trim()) return

    try {
      await createRule({
        category: newCat,
        pattern: newPattern.trim(),
        rule_type: newType,
        priority: newPriority,
        is_active: true,
      })
      setNewPattern('')
      setAddingRule(false)
      setSavedMessage('Rule created and applied successfully!')
      setTimeout(() => setSavedMessage(''), 3000)
      const r = await getRules()
      setRules(r)
    } catch (err) {
      console.error('Failed to create rule', err)
    }
  }

  const handleDeleteRule = async (id: string) => {
    try {
      await deleteRule(id)
      const r = await getRules()
      setRules(r)
    } catch (err) {
      console.error('Failed to delete rule', err)
    }
  }

  return (
    <div className="page" style={{ paddingTop: 28, maxWidth: 1200 }}>
      <div style={{ marginBottom: 24 }}>
        <h2 style={{ fontSize: 22, fontWeight: 700, margin: '0 0 6px', letterSpacing: '-0.3px' }}>
          Settings & Classification Rules
        </h2>
        <p style={{ color: 'var(--muted)', fontSize: 13, margin: 0 }}>
          Configure deterministic keyword heuristics, ML confidence thresholds, and on-premise privacy defaults.
        </p>
      </div>

      {savedMessage && (
        <div
          style={{
            padding: '12px 16px',
            borderRadius: 10,
            background: '#eaf9f3',
            color: '#07825f',
            fontSize: 13,
            fontWeight: 500,
            marginBottom: 20,
            display: 'flex',
            alignItems: 'center',
            gap: 8,
            border: '1px solid #c2ebd9',
          }}
        >
          <CheckCircle2 size={16} />
          {savedMessage}
        </div>
      )}

      <div
        style={{
          display: 'grid',
          gridTemplateColumns: 'minmax(0, 1.45fr) minmax(0, 1fr)',
          gap: 24,
          alignItems: 'start',
        }}
      >
        {/* Left Column: Rules & Privacy */}
        <div style={{ display: 'flex', flexDirection: 'column', gap: 20, minWidth: 0 }}>
          {/* User Rule Overrides */}
          <section className="card" style={{ padding: '24px' }}>
            <div className="card-head" style={{ marginBottom: 18 }}>
              <div>
                <h3 style={{ fontSize: 15, fontWeight: 650 }}>User Rule Overrides</h3>
                <p style={{ fontSize: 11 }}>Custom pattern definitions stored in SQLite (priority overrides)</p>
              </div>
              <Button icon={<Plus size={14} />} onClick={() => setAddingRule(!addingRule)}>
                {addingRule ? 'Cancel' : 'Add Custom Rule'}
              </Button>
            </div>

            {addingRule && (
              <form
                onSubmit={handleAddRule}
                style={{
                  padding: 18,
                  background: 'var(--soft)',
                  borderRadius: 10,
                  marginBottom: 18,
                  border: '1px solid var(--line)',
                }}
              >
                <h4 style={{ margin: '0 0 12px', fontSize: 13, fontWeight: 600 }}>New Deterministic Rule</h4>
                <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 12, marginBottom: 12 }}>
                  <div>
                    <label style={{ display: 'block', fontSize: 10, fontWeight: 700, color: 'var(--muted)', marginBottom: 5 }}>
                      CATEGORY
                    </label>
                    <select
                      className="filter-select"
                      style={{ width: '100%', height: 38 }}
                      value={newCat}
                      onChange={(e) => setNewCat(e.target.value)}
                    >
                      {CATEGORIES.map((c) => (
                        <option key={c} value={c}>
                          {c}
                        </option>
                      ))}
                    </select>
                  </div>
                  <div>
                    <label style={{ display: 'block', fontSize: 10, fontWeight: 700, color: 'var(--muted)', marginBottom: 5 }}>
                      MATCH TYPE
                    </label>
                    <select
                      className="filter-select"
                      style={{ width: '100%', height: 38 }}
                      value={newType}
                      onChange={(e) => setNewType(e.target.value as any)}
                    >
                      <option value="keyword">Keyword (Substring)</option>
                      <option value="regex">Regular Expression</option>
                    </select>
                  </div>
                </div>

                <div style={{ display: 'grid', gridTemplateColumns: '2fr 1fr', gap: 12, marginBottom: 14 }}>
                  <div>
                    <label style={{ display: 'block', fontSize: 10, fontWeight: 700, color: 'var(--muted)', marginBottom: 5 }}>
                      PATTERN
                    </label>
                    <input
                      type="text"
                      placeholder="e.g. STARBUCKS or (?i)spotify.*premium"
                      value={newPattern}
                      onChange={(e) => setNewPattern(e.target.value)}
                      style={{
                        width: '100%',
                        height: 38,
                        border: '1px solid var(--line)',
                        borderRadius: 8,
                        padding: '0 12px',
                        fontSize: 12,
                        background: 'var(--surface)',
                        color: 'var(--ink)',
                        outline: 'none',
                      }}
                    />
                  </div>
                  <div>
                    <label style={{ display: 'block', fontSize: 10, fontWeight: 700, color: 'var(--muted)', marginBottom: 5 }}>
                      PRIORITY (1-100)
                    </label>
                    <input
                      type="number"
                      min={1}
                      max={100}
                      value={newPriority}
                      onChange={(e) => setNewPriority(Number(e.target.value))}
                      style={{
                        width: '100%',
                        height: 38,
                        border: '1px solid var(--line)',
                        borderRadius: 8,
                        padding: '0 12px',
                        fontSize: 12,
                        background: 'var(--surface)',
                        color: 'var(--ink)',
                        outline: 'none',
                      }}
                    />
                  </div>
                </div>

                <div style={{ display: 'flex', justifyContent: 'flex-end', gap: 8 }}>
                  <Button variant="secondary" type="button" onClick={() => setAddingRule(false)}>
                    Cancel
                  </Button>
                  <Button type="submit">Save Rule</Button>
                </div>
              </form>
            )}

            <div className="table-scroll">
              <table className="rules-table">
                <thead>
                  <tr>
                    <th>Category</th>
                    <th>Type</th>
                    <th>Pattern</th>
                    <th>Priority</th>
                    <th style={{ width: 40, textAlign: 'center' }}>Action</th>
                  </tr>
                </thead>
                <tbody>
                  {rules.map((r) => (
                    <tr key={r.id}>
                      <td>
                        <strong>{r.category}</strong>
                      </td>
                      <td>
                        <Badge tone={r.rule_type === 'regex' ? 'purple' : 'blue'}>
                          {r.rule_type}
                        </Badge>
                      </td>
                      <td>
                        <code
                          style={{
                            fontSize: 11,
                            background: 'var(--soft)',
                            padding: '3px 7px',
                            borderRadius: 4,
                            border: '1px solid var(--line)',
                          }}
                        >
                          {r.pattern}
                        </code>
                      </td>
                      <td>{r.priority}</td>
                      <td style={{ textAlign: 'center' }}>
                        <button
                          className="icon-button"
                          onClick={() => handleDeleteRule(r.id)}
                          title="Delete rule"
                          style={{ color: '#ef5b5b', width: 28, height: 28 }}
                        >
                          <Trash2 size={13} />
                        </button>
                      </td>
                    </tr>
                  ))}
                  {rules.length === 0 && (
                    <tr>
                      <td colSpan={5} style={{ textAlign: 'center', color: 'var(--muted)', padding: '28px 16px' }}>
                        Defaulting to 150+ built-in base YAML classification rules. Click "Add Custom Rule" to add overrides.
                      </td>
                    </tr>
                  )}
                </tbody>
              </table>
            </div>
          </section>

          {/* Privacy & Security Posture */}
          <section className="card" style={{ padding: '24px' }}>
            <div className="card-head" style={{ marginBottom: 16 }}>
              <div>
                <h3 style={{ fontSize: 15, fontWeight: 650 }}>Security & Privacy Posture</h3>
                <p style={{ fontSize: 11 }}>StatementIQ financial data handling controls</p>
              </div>
              <ShieldCheck size={22} color="#07825f" />
            </div>

            <div style={{ display: 'flex', flexDirection: 'column', gap: 14 }}>
              <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                <div>
                  <strong style={{ fontSize: 13, display: 'block', color: 'var(--ink)' }}>Account Number Masking</strong>
                  <small style={{ color: 'var(--muted)', fontSize: 11 }}>
                    Masks sensitive account numbers in logs, UI, and exports (shows only last 4 digits)
                  </small>
                </div>
                <Badge tone="green">Enforced Always</Badge>
              </div>

              <div
                style={{
                  display: 'flex',
                  justifyContent: 'space-between',
                  alignItems: 'center',
                  borderTop: '1px solid var(--line)',
                  paddingTop: 12,
                }}
              >
                <div>
                  <strong style={{ fontSize: 13, display: 'block', color: 'var(--ink)' }}>Zero External AI Transmission</strong>
                  <small style={{ color: 'var(--muted)', fontSize: 11 }}>
                    All extraction and ML classification strictly run locally. No OpenAI, Gemini, or Claude API calls.
                  </small>
                </div>
                <Badge tone="green">Air-Gapped</Badge>
              </div>

              <div
                style={{
                  display: 'flex',
                  justifyContent: 'space-between',
                  alignItems: 'center',
                  borderTop: '1px solid var(--line)',
                  paddingTop: 12,
                }}
              >
                <div>
                  <strong style={{ fontSize: 13, display: 'block', color: 'var(--ink)' }}>Temporary PDF Upload Purging</strong>
                  <small style={{ color: 'var(--muted)', fontSize: 11 }}>
                    Uploaded PDF binaries are automatically unlinked after transaction extraction completes.
                  </small>
                </div>
                <Badge tone="indigo">Active</Badge>
              </div>
            </div>
          </section>
        </div>

        {/* Right Column: Classification Controls & Retention */}
        <div style={{ display: 'flex', flexDirection: 'column', gap: 20, minWidth: 0 }}>
          {/* Classification Controls */}
          <section className="card" style={{ padding: '24px' }}>
            <div className="card-head" style={{ marginBottom: 14 }}>
              <div>
                <h3 style={{ fontSize: 15, fontWeight: 650 }}>Classification Controls</h3>
                <p style={{ fontSize: 11 }}>Tune the threshold for deterministic routing</p>
              </div>
              <Sliders size={18} color="var(--primary)" />
            </div>

            <div style={{ marginBottom: 8 }}>
              <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 10 }}>
                <label style={{ fontSize: 11, fontWeight: 700, color: 'var(--muted)', letterSpacing: '0.4px' }}>
                  ML CONFIDENCE THRESHOLD
                </label>
                <span
                  style={{
                    fontSize: 14,
                    fontWeight: 700,
                    color: 'var(--primary)',
                    background: 'var(--soft)',
                    padding: '2px 8px',
                    borderRadius: 6,
                    border: '1px solid var(--line)',
                  }}
                >
                  {threshold}%
                </span>
              </div>
              <input
                type="range"
                min="50"
                max="95"
                value={threshold}
                onChange={(e) => handleThresholdChange(Number(e.target.value))}
                style={{ width: '100%', accentColor: 'var(--primary)', height: 6, cursor: 'pointer' }}
              />
              <p style={{ color: 'var(--muted)', fontSize: 11, marginTop: 10, lineHeight: 1.5, margin: '10px 0 0' }}>
                Predictions below <strong>{threshold}%</strong> confidence will route directly to the Review Queue as Uncategorized.
              </p>
            </div>
          </section>

          {/* Retention Settings */}
          <section className="card" style={{ padding: '24px' }}>
            <div className="card-head" style={{ marginBottom: 16 }}>
              <div>
                <h3 style={{ fontSize: 15, fontWeight: 650 }}>Data Retention Policy</h3>
                <p style={{ fontSize: 11 }}>Control persistence of extracted transaction history</p>
              </div>
              <Database size={18} color="var(--primary)" />
            </div>

            <div
              style={{
                display: 'flex',
                justifyContent: 'space-between',
                alignItems: 'center',
                padding: '14px 16px',
                background: 'var(--soft)',
                borderRadius: 10,
                border: '1px solid var(--line)',
                cursor: 'pointer',
              }}
              onClick={() => handleToggleRetention(!retention)}
            >
              <div style={{ paddingRight: 16 }}>
                <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
                  <span style={{ fontSize: 13, fontWeight: 600, color: 'var(--ink)' }}>
                    Auto-Purge Extracted Data
                  </span>
                  <Badge tone={retention ? 'indigo' : 'neutral'}>
                    {retention ? 'Active' : 'Off'}
                  </Badge>
                </div>
                <small style={{ color: 'var(--muted)', fontSize: 11, lineHeight: 1.4, display: 'block', marginTop: 4 }}>
                  {retention
                    ? 'Records will be purged from SQLite upon browser session termination.'
                    : 'Off by default for auditability. Records persist securely in local SQLite until manually deleted.'}
                </small>
              </div>
              <div onClick={(e) => e.stopPropagation()}>
                <Switch
                  checked={retention}
                  onChange={handleToggleRetention}
                  ariaLabel="Toggle auto-purge extracted data"
                />
              </div>
            </div>

          </section>
        </div>
      </div>
    </div>
  )
}
