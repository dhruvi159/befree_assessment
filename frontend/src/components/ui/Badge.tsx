import React from 'react'

interface BadgeProps {
  children: React.ReactNode
  tone?: string
  className?: string
}

export function Badge({ children, tone = 'neutral', className = '' }: BadgeProps) {
  return <span className={`badge ${tone} ${className}`}>{children}</span>
}

