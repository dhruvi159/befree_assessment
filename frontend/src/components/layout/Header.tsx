import React from 'react'
import { Moon, Sun, Bell, Menu, Shield } from 'lucide-react'
import type { Page } from '../../types'

interface HeaderProps {
  page: Page
  dark: boolean
  setDark: (d: boolean) => void
  setMobileOpen: (o: boolean) => void
  isProcessing?: boolean
}

const titles: Record<Page, { title: string; subtitle: string }> = {
  dashboard: {
    title: 'Financial Dashboard',
    subtitle: 'Overview of processed statement metrics and spend distribution',
  },
  upload: {
    title: 'Upload Bank Statement',
    subtitle: 'Extract, classify, and validate transactions from real statements',
  },
  transactions: {
    title: 'Transactions Workspace',
    subtitle: 'Review, edit, categorize, and validate extracted transaction entries',
  },
  classification: {
    title: 'Classification & Intelligence',
    subtitle: 'Rule-based and Machine Learning categorization coverage',
  },
  reports: {
    title: 'Reports & Analytics',
    subtitle: 'Financial insights, income vs expenditure, and merchant summaries',
  },
  settings: {
    title: 'System Settings & Rules',
    subtitle: 'Manage deterministic rules, model confidence thresholds, and taxonomy',
  },
}

export function Header({ page, dark, setDark, setMobileOpen, isProcessing }: HeaderProps) {
  const current = titles[page]

  return (
    <header className="topbar">
      <div className="title-wrap">
        <button className="menu-btn" onClick={() => setMobileOpen(true)}>
          <Menu size={18} />
        </button>
        <div>
          <h1>{current.title}</h1>
          <p>{current.subtitle}</p>
        </div>
      </div>

      <div className="top-actions">
        {isProcessing && (
          <div
            style={{
              display: 'flex',
              alignItems: 'center',
              gap: 6,
              background: '#eeeeff',
              color: '#4444db',
              padding: '6px 12px',
              borderRadius: 20,
              fontSize: 11,
              fontWeight: 600,
            }}
          >
            <span className="pulse-dot" /> Processing Statement...
          </div>
        )}

        <button
          className="icon-button"
          onClick={() => setDark(!dark)}
          aria-label="Toggle theme"
          title={dark ? 'Switch to light mode' : 'Switch to dark mode'}
        >
          {dark ? <Sun size={17} /> : <Moon size={17} />}
        </button>

        <button className="icon-button notification" aria-label="Privacy notice" title="Zero External AI - Local ML Only">
          <Shield size={17} />
        </button>

        <div className="profile">
          <div className="avatar">SI</div>
          <div>
            <strong>Reviewer</strong>
            <span>Local Analyst</span>
          </div>
        </div>
      </div>
    </header>
  )
}

