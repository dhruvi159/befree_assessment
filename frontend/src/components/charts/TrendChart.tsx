import React from 'react'
import {
  BarChart,
  Bar,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  ResponsiveContainer,
} from 'recharts'
import type { MonthlyTrend } from '../../types'
import { formatINR, formatMonth } from '../../utils/format'

interface TrendChartProps {
  data: MonthlyTrend[]
}

function CustomTooltip({ active, payload, label }: any) {
  if (!active || !payload || !payload.length) return null
  return (
    <div
      style={{
        background: 'var(--surface)',
        border: '1px solid var(--line)',
        borderRadius: 8,
        padding: '8px 12px',
        fontSize: 11,
        color: 'var(--ink)',
        boxShadow: 'var(--shadow)',
        minWidth: 140,
      }}
    >
      <div style={{ fontWeight: 600, marginBottom: 6, color: 'var(--muted)' }}>{label}</div>
      {payload.map((p: any) => (
        <div key={p.name} style={{ display: 'flex', justifyContent: 'space-between', gap: 16, marginBottom: 2 }}>
          <span style={{ color: p.fill, fontWeight: 600 }}>{p.name}</span>
          <span style={{ fontWeight: 700 }}>{formatINR(Number(p.value))}</span>
        </div>
      ))}
    </div>
  )
}

export function TrendChart({ data }: TrendChartProps) {
  if (!data || data.length === 0) {
    return (
      <div style={{ height: 220, display: 'grid', placeItems: 'center', color: '#6d7588', fontSize: 12 }}>
        No historical trends found
      </div>
    )
  }

  const chartData = data.map((d) => ({
    month: formatMonth(d.month),
    Credits: d.credits,
    Debits: d.debits,
  }))

  return (
    <div style={{ width: '100%', height: 230, paddingTop: 10 }}>
      <ResponsiveContainer width="100%" height="100%">
        <BarChart data={chartData} margin={{ top: 10, right: 10, left: 0, bottom: 0 }}>
          <CartesianGrid strokeDasharray="3 3" stroke="var(--line)" vertical={false} />
          <XAxis dataKey="month" stroke="var(--muted)" fontSize={10} tickLine={false} />
          <YAxis
            stroke="var(--muted)"
            fontSize={9}
            tickLine={false}
            tickFormatter={(val) => `\u20b9${(val / 1000).toFixed(0)}k`}
          />
          <Tooltip content={<CustomTooltip />} />
          <Bar dataKey="Credits" fill="#07825f" radius={[4, 4, 0, 0]} />
          <Bar dataKey="Debits" fill="#ef5b5b" radius={[4, 4, 0, 0]} />
        </BarChart>
      </ResponsiveContainer>
    </div>
  )
}