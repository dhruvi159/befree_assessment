import React, { useState, useRef } from 'react'
import {
  Upload as UploadIcon,
  FileText,
  Lock,
  ShieldCheck,
  CheckCircle2,
  AlertCircle,
  Clock,
  ArrowRight,
  Layers,
} from 'lucide-react'
import type { Page, StatementStatus } from '../types'
import { uploadStatement, getStatementStatus } from '../api/client'
import { Button } from '../components/ui/Button'
import { Badge } from '../components/ui/Badge'
import { formatFileSize } from '../utils/format'

interface UploadPageProps {
  setPage: (p: Page) => void
}

const PIPELINE_STAGES = [
  { id: 'detecting', label: 'PDF Detection' },
  { id: 'extracting', label: 'Text Extraction / OCR' },
  { id: 'standardizing', label: 'Standardization' },
  { id: 'classifying', label: 'Classification' },
  { id: 'validating', label: 'Financial Validation' },
  { id: 'completed', label: 'Review & Export' },
]

export function Upload({ setPage }: UploadPageProps) {
  const [file, setFile] = useState<File | null>(null)
  const [password, setPassword] = useState('')
  const [dragging, setDragging] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [processingStatus, setProcessingStatus] = useState<StatementStatus | null>(null)
  const [isUploading, setIsUploading] = useState(false)
  const fileInputRef = useRef<HTMLInputElement>(null)

  const handleFileDrop = (e: React.DragEvent) => {
    e.preventDefault()
    setDragging(false)
    setError(null)
    const droppedFile = e.dataTransfer.files[0]
    validateAndSetFile(droppedFile)
  }

  const handleFileSelect = (e: React.ChangeEvent<HTMLInputElement>) => {
    if (e.target.files && e.target.files[0]) {
      setError(null)
      validateAndSetFile(e.target.files[0])
    }
  }

  const validateAndSetFile = (f: File) => {
    if (!f.name.toLowerCase().endsWith('.pdf')) {
      setError('Only PDF documents are supported. Please select a valid bank statement PDF.')
      return
    }
    if (f.size > 25 * 1024 * 1024) {
      setError('File size exceeds the 25 MB limit.')
      return
    }
    setFile(f)
  }

  const handleUploadAndProcess = async () => {
    if (!file) return
    setError(null)
    setIsUploading(true)

    try {
      const stmt = await uploadStatement(file, password || undefined)

      // Start polling status
      const pollInterval = setInterval(async () => {
        try {
          const status = await getStatementStatus(stmt.id)
          setProcessingStatus(status)

          if (status.status === 'completed' || status.status === 'failed') {
            clearInterval(pollInterval)
            setIsUploading(false)
            if (status.status === 'failed') {
              setError(status.error_message || 'Statement processing failed.')
            }
          }
        } catch (pollErr) {
          console.error('Polling error', pollErr)
        }
      }, 1500)
    } catch (err: any) {
      setIsUploading(false)
      const detail = err.response?.data?.detail || err.message || 'Upload failed'
      setError(detail)
    }
  }

  const getStageIndex = (status: string | undefined): number => {
    if (!status) return 0
    if (status === 'completed') return 5
    if (status === 'validating') return 4
    if (status === 'classifying') return 3
    if (status === 'standardizing') return 2
    if (status === 'extracting') return 1
    if (status === 'detecting') return 0
    return 0
  }

  const currentStageIdx = getStageIndex(processingStatus?.status)

  return (
    <div className="page narrow-page">
      <div className="page-heading">
        <div>
          <Badge tone="indigo">
            <ShieldCheck size={13} /> INTELLIGENT BANK STATEMENT ENGINE
          </Badge>
          <h2>Process Real Bank Statements</h2>
          <p>
            Upload your PDF bank statements. Our deterministic rules and local TF-IDF machine learning pipeline will automatically parse, classify, and reconcile every transaction.
          </p>
        </div>
      </div>

      {/* Error notification */}
      {error && (
        <div
          style={{
            marginBottom: 20,
            padding: '12px 16px',
            borderRadius: 10,
            background: '#fdf3f4',
            border: '1px solid #f5c6cb',
            color: '#721c24',
            display: 'flex',
            alignItems: 'center',
            gap: 10,
            fontSize: 12,
          }}
        >
          <AlertCircle size={18} />
          <span>{error}</span>
        </div>
      )}

      {/* Upload Box */}
      {!isUploading && !processingStatus?.status ? (
        <>
          <section
            className={`upload-zone ${dragging ? 'dragging' : ''}`}
            onDragOver={(e) => {
              e.preventDefault()
              setDragging(true)
            }}
            onDragLeave={() => setDragging(false)}
            onDrop={handleFileDrop}
            onClick={() => fileInputRef.current?.click()}
          >
            <input
              type="file"
              ref={fileInputRef}
              style={{ display: 'none' }}
              accept=".pdf"
              onChange={handleFileSelect}
            />
            <div className="upload-icon">
              <UploadIcon size={28} />
            </div>
            <h3>Drop your bank statement PDF here</h3>
            <p>
              or <button type="button" onClick={(e) => { e.stopPropagation(); fileInputRef.current?.click() }}>browse files</button> from your device
            </p>
            <small>Supports all Indian & International bank statement formats (Max 25 MB)</small>
          </section>

          {/* Password Protection Field */}
          <div className="password-row">
            <div>
              <Lock size={17} />
              <span>Password Protected PDF?</span>
            </div>
            <input
              type="password"
              placeholder="Enter PDF password (if required by your bank)"
              value={password}
              onChange={(e) => setPassword(e.target.value)}
            />
          </div>

          {/* Selected File Card */}
          <div className="section-label">
            <span>SELECTED DOCUMENT</span>
            <b>{file ? '1 file ready' : 'No file selected'}</b>
          </div>

          {file ? (
            <div className="file-card">
              <div className="pdf-icon">PDF</div>
              <div className="file-info">
                <strong>{file.name}</strong>
                <span>{formatFileSize(file.size)} · Ready for extraction</span>
                <div className="file-ready">
                  <CheckCircle2 size={13} /> Validated PDF document
                </div>
              </div>
              <Button
                variant="ghost"
                onClick={() => setFile(null)}
                style={{ color: '#ef5b5b', fontSize: 11 }}
              >
                Remove
              </Button>
            </div>
          ) : (
            <div className="empty-file">
              <FileText size={18} />
              <span>No document uploaded yet</span>
            </div>
          )}

          {/* Action Footer */}
          <div className="upload-footer">
            <div>
              <ShieldCheck size={20} color="#07825f" />
              <span>
                100% On-Premise Privacy
                <br />
                <small>Account numbers are automatically masked (last 4 digits only)</small>
              </span>
            </div>
            <Button
              disabled={!file}
              onClick={handleUploadAndProcess}
              icon={<ArrowRight size={16} />}
            >
              Start Extraction Pipeline
            </Button>
          </div>
        </>
      ) : (
        /* Live Pipeline Progress Screen */
        <div className="card" style={{ padding: '32px 24px' }}>
          <div style={{ textAlign: 'center', marginBottom: 28 }}>
            <span className="pulse-dot" style={{ display: 'inline-block', marginBottom: 10 }} />
            <h3 style={{ fontSize: 20, margin: '0 0 6px', fontWeight: 650 }}>
              {processingStatus?.status === 'completed'
                ? 'Processing Complete!'
                : processingStatus?.status === 'failed'
                ? 'Processing Encountered an Issue'
                : 'Intelligent Processing in Progress'}
            </h3>
            <p style={{ color: 'var(--muted)', fontSize: 12, margin: 0 }}>
              {processingStatus?.processing_message || 'Analyzing bank statement structure...'}
            </p>
          </div>

          {/* Stepper */}
          <div className="stepper" style={{ marginBottom: 36 }}>
            {PIPELINE_STAGES.map((stage, idx) => {
              const isDone = currentStageIdx > idx || processingStatus?.status === 'completed'
              const isCurrent = currentStageIdx === idx && processingStatus?.status !== 'completed'

              return (
                <div
                  key={stage.id}
                  className={`step ${isDone ? 'done' : isCurrent ? 'current' : ''}`}
                >
                  <div className="step-dot">
                    {isDone ? <CheckCircle2 size={14} /> : idx + 1}
                  </div>
                  <span>{stage.label}</span>
                  {idx < PIPELINE_STAGES.length - 1 && <i />}
                </div>
              )
            })}
          </div>

          {/* Metadata Card */}
          <div className="process-metrics">
            <div>
              <span>PDF Structure</span>
              <strong>
                <i className="type-dot blue" /> {processingStatus?.pdf_type || 'Detecting...'}
              </strong>
            </div>
            <div>
              <span>Total Pages</span>
              <strong>{processingStatus?.page_count || 'Scanning...'}</strong>
            </div>
            <div>
              <span>Progress</span>
              <strong>{Math.round(processingStatus?.processing_progress || 0)}%</strong>
            </div>
            <div>
              <span>ML Engine</span>
              <strong>TF-IDF + Rules</strong>
            </div>
          </div>

          {/* Page Type breakdown */}
          {processingStatus?.page_types && processingStatus.page_types.length > 0 && (
            <div style={{ marginTop: 20 }}>
              <span style={{ fontSize: 11, color: 'var(--muted)', fontWeight: 600 }}>PAGE CLASSIFICATION:</span>
              <div style={{ display: 'flex', gap: 6, flexWrap: 'wrap', marginTop: 8 }}>
                {processingStatus.page_types.map((p) => (
                  <Badge key={p.page} tone={p.type === 'text' ? 'blue' : 'amber'}>
                    Page {p.page}: {p.type === 'text' ? 'Digital Text' : 'Scanned Image (OCR)'}
                  </Badge>
                ))}
              </div>
            </div>
          )}

          {/* Complete Actions */}
          {processingStatus?.status === 'completed' && (
            <div style={{ marginTop: 28, display: 'flex', justifyContent: 'center', gap: 12 }}>
              <Button variant="secondary" onClick={() => { setProcessingStatus(null); setFile(null); }}>
                Upload Another Statement
              </Button>
              <Button onClick={() => setPage('transactions')} icon={<ArrowRight size={15} />}>
                Inspect Transactions
              </Button>
            </div>
          )}

          {processingStatus?.status === 'failed' && (
            <div style={{ marginTop: 28, textAlign: 'center' }}>
              <Button variant="secondary" onClick={() => { setProcessingStatus(null); }}>
                Retry Upload
              </Button>
            </div>
          )}
        </div>
      )}
    </div>
  )
}

