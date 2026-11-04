import React, { useState } from 'react'
import { Download, FileSpreadsheet, FileText, Check, X } from 'lucide-react'
import { Button } from './ui/Button'
import { exportExcel, exportCSV, downloadBlob } from '../api/client'

interface ExportModalProps {
  statementId: string
  statementFilename?: string
  onClose: () => void
}

export function ExportModal({ statementId, statementFilename = 'Statement', onClose }: ExportModalProps) {
  const [format, setFormat] = useState<'excel' | 'csv'>('excel')
  const [downloading, setDownloading] = useState(false)
  const [downloaded, setDownloaded] = useState(false)

  const handleDownload = async () => {
    try {
      setDownloading(true)
      const baseName = statementFilename.replace(/\.pdf$/i, '')
      if (format === 'excel') {
        const blob = await exportExcel(statementId)
        downloadBlob(blob, `${baseName}_StatementIQ.xlsx`)
      } else {
        const blob = await exportCSV(statementId)
        downloadBlob(blob, `${baseName}_StatementIQ.csv`)
      }
      setDownloaded(true)
    } catch (err) {
      console.error('Download error', err)
    } finally {
      setDownloading(false)
    }
  }

  return (
    <>
      <div className="overlay" onClick={onClose} />
      <div className="modal">
        <div className="modal-icon">
          {downloaded ? <Check size={26} color="#07825f" /> : <Download size={26} />}
        </div>
        <h2>{downloaded ? 'Export Downloaded!' : 'Export Financial Data'}</h2>
        <p>
          {downloaded
            ? 'Your processed bank statement report has been saved.'
            : 'Select your preferred export format for audit, accounting, and analytics.'}
        </p>

        <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 12, marginBottom: 20 }}>
          <button
            style={{
              padding: 14,
              border: `1.5px solid ${format === 'excel' ? 'var(--primary)' : 'var(--line)'}`,
              borderRadius: 12,
              background: format === 'excel' ? '#eeeeff' : 'var(--surface)',
              textAlign: 'left',
              display: 'flex',
              alignItems: 'center',
              gap: 10,
              cursor: 'pointer',
            }}
            onClick={() => setFormat('excel')}
          >
            <div className="format-icon excel">
              <FileSpreadsheet size={18} />
            </div>
            <div>
              <strong style={{ display: 'block', fontSize: 12 }}>Excel (.xlsx)</strong>
              <small style={{ color: 'var(--muted)', fontSize: 10 }}>Multi-sheet report</small>
            </div>
          </button>

          <button
            style={{
              padding: 14,
              border: `1.5px solid ${format === 'csv' ? 'var(--primary)' : 'var(--line)'}`,
              borderRadius: 12,
              background: format === 'csv' ? '#eeeeff' : 'var(--surface)',
              textAlign: 'left',
              display: 'flex',
              alignItems: 'center',
              gap: 10,
              cursor: 'pointer',
            }}
            onClick={() => setFormat('csv')}
          >
            <div className="format-icon csv">
              <FileText size={18} />
            </div>
            <div>
              <strong style={{ display: 'block', fontSize: 12 }}>CSV (.csv)</strong>
              <small style={{ color: 'var(--muted)', fontSize: 10 }}>Standard flat file</small>
            </div>
          </button>
        </div>

        <div className="download-file">
          <div className={`format-icon ${format}`}>
            {format === 'excel' ? <FileSpreadsheet size={18} /> : <FileText size={18} />}
          </div>
          <div>
            <strong>
              {statementFilename.replace(/\.pdf$/i, '')}_StatementIQ.{format === 'excel' ? 'xlsx' : 'csv'}
            </strong>
            <span>Verified reconciliation & masked account numbers</span>
          </div>
        </div>

        <div className="modal-actions">
          <Button variant="secondary" onClick={onClose}>
            Close
          </Button>
          <Button icon={<Download size={15} />} onClick={handleDownload} disabled={downloading}>
            {downloading ? 'Exporting...' : downloaded ? 'Download Again' : 'Download Report'}
          </Button>
        </div>
      </div>
    </>
  )
}

