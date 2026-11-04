import React from 'react'
import { FileQuestion, Upload } from 'lucide-react'
import { Button } from './Button'

interface EmptyStateProps {
  title: string
  description: string
  onAction?: () => void
  actionLabel?: string
  icon?: React.ReactNode
}

export function EmptyState({
  title,
  description,
  onAction,
  actionLabel = 'Upload Statement',
  icon,
}: EmptyStateProps) {
  return (
    <div className="card" style={{ padding: '48px 24px', textAlign: 'center' }}>
      <div
        style={{
          width: 56,
          height: 56,
          borderRadius: 16,
          background: '#eeeeff',
          color: '#4444db',
          display: 'grid',
          placeItems: 'center',
          margin: '0 auto 16px',
        }}
      >
        {icon || <FileQuestion size={28} />}
      </div>
      <h3 style={{ fontSize: 18, margin: '0 0 8px', fontWeight: 650 }}>{title}</h3>
      <p style={{ color: '#6d7588', fontSize: 13, maxWidth: 440, margin: '0 auto 24px' }}>
        {description}
      </p>
      {onAction && (
        <Button onClick={onAction} icon={<Upload size={16} />}>
          {actionLabel}
        </Button>
      )}
    </div>
  )
}

