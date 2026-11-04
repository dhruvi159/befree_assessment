import React, { useState, useEffect } from 'react'
import { Sidebar } from './Sidebar'
import { Header } from './Header'
import type { Page } from '../../types'

interface LayoutProps {
  page: Page
  setPage: (p: Page) => void
  children: React.ReactNode
  flaggedCount?: number
  isProcessing?: boolean
}

export function Layout({
  page,
  setPage,
  children,
  flaggedCount = 0,
  isProcessing = false,
}: LayoutProps) {
  const [dark, setDark] = useState(() => {
    if (typeof window !== 'undefined') {
      const saved = localStorage.getItem('statementiq_theme')
      if (saved) return saved === 'dark'
      return window.matchMedia('(prefers-color-scheme: dark)').matches
    }
    return false
  })
  const [collapsed, setCollapsed] = useState(false)
  const [mobileOpen, setMobileOpen] = useState(false)

  useEffect(() => {
    if (dark) {
      document.documentElement.classList.add('dark')
      document.body.classList.add('dark')
      localStorage.setItem('statementiq_theme', 'dark')
    } else {
      document.documentElement.classList.remove('dark')
      document.body.classList.remove('dark')
      localStorage.setItem('statementiq_theme', 'light')
    }
  }, [dark])

  return (
    <div className={`app ${dark ? 'dark' : ''}`}>
      <Sidebar
        page={page}
        setPage={setPage}
        collapsed={collapsed}
        setCollapsed={setCollapsed}
        mobileOpen={mobileOpen}
        setMobileOpen={setMobileOpen}
        flaggedCount={flaggedCount}
      />
      {mobileOpen && (
        <div className="mobile-overlay" onClick={() => setMobileOpen(false)} />
      )}
      <main className="main">
        <Header
          page={page}
          dark={dark}
          setDark={setDark}
          setMobileOpen={setMobileOpen}
          isProcessing={isProcessing}
        />
        {children}
      </main>
    </div>
  )
}

