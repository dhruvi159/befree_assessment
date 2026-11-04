import React, { useState, useEffect } from 'react'
import type { Page } from './types'
import { Layout } from './components/layout/Layout'
import { Dashboard } from './pages/Dashboard'
import { Upload } from './pages/Upload'
import { Transactions } from './pages/Transactions'
import { Classification } from './pages/Classification'
import { Reports } from './pages/Reports'
import { Settings } from './pages/Settings'
import { getStatements } from './api/client'

export default function App() {
  const [page, setPage] = useState<Page>('dashboard')
  const [flaggedCount, setFlaggedCount] = useState<number>(0)
  const [isProcessing, setIsProcessing] = useState<boolean>(false)

  // Auto-purge on browser session termination if retention is enabled
  useEffect(() => {
    const handleSessionEnd = () => {
      const isRetentionActive = localStorage.getItem('statementiq_retention') === 'true'
      if (isRetentionActive && navigator.sendBeacon) {
        navigator.sendBeacon('/api/statements/purge')
      }
    }

    window.addEventListener('beforeunload', handleSessionEnd)
    window.addEventListener('pagehide', handleSessionEnd)
    return () => {
      window.removeEventListener('beforeunload', handleSessionEnd)
      window.removeEventListener('pagehide', handleSessionEnd)
    }
  }, [])

  // Check statement status on mount and page switch
  useEffect(() => {
    async function checkProcessing() {
      try {
        const stmts = await getStatements()
        const processing = stmts.some(
          (s) =>
            s.status !== 'completed' &&
            s.status !== 'failed' &&
            s.status !== 'uploaded'
        )
        setIsProcessing(processing)
      } catch (err) {
        // quiet error on initial startup
      }
    }
    checkProcessing()
  }, [page])

  return (
    <Layout
      page={page}
      setPage={setPage}
      flaggedCount={flaggedCount}
      isProcessing={isProcessing}
    >
      {page === 'dashboard' && <Dashboard setPage={setPage} />}
      {page === 'upload' && <Upload setPage={setPage} />}
      {page === 'transactions' && <Transactions setPage={setPage} />}
      {page === 'classification' && <Classification setPage={setPage} />}
      {page === 'reports' && <Reports setPage={setPage} />}
      {page === 'settings' && <Settings setPage={setPage} />}
    </Layout>
  )
}

