import React from 'react'

interface StatCardProps {
  label: string
  value: string
  change?: string
  icon: React.ReactNode
  tone?: 'teal' | 'indigo' | 'blue' | 'purple' | 'amber'
}

export function StatCard({ label, value, change, icon, tone = 'indigo' }: StatCardProps) {
  return (
    <div className="stat-card">
      <div className={`stat-icon ${tone}`}>{icon}</div>
      <div className="stat-content">
        <span>{label}</span>
        <strong>{value}</strong>
        {change && (
          <small
            className={
              change.startsWith('+')
                ? 'positive'
                : change.startsWith('-')
                ? 'negative'
                : ''
            }
          >
            {change}
          </small>
        )}
      </div>
    </div>
  )
}

