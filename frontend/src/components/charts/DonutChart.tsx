import React from 'react'
import { PieChart, Pie, Cell, ResponsiveContainer, Tooltip } from 'recharts'
import type { CategoryBreakdown } from '../../types'
import { getCategoryHexColor, formatINR } from '../../utils/format'

interface DonutChartProps {
  data: CategoryBreakdown[]
}

// Custom tooltip so we fully control its appearance in both light and dark themes
function CustomTooltip({ active, payload }: any) {
  if (!active || !payload || !payload.length) return null
  const { name, value, color, percentage } = payload[0].payload
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
        minWidth: 120,
      }}
    >
      <div style={{ display: 'flex', alignItems: 'center', gap: 6, marginBottom: 4 }}>
        <i style={{ width: 8, height: 8, borderRadius: 2, background: color, display: 'inline-block', flexShrink: 0 }} />
        <span style={{ fontWeight: 600 }}>{name}</span>
      </div>
      <div style={{ color: 'var(--ink)', fontWeight: 700 }}>{formatINR(Number(value))}</div>
      <div style={{ color: 'var(--muted)', fontSize: 10 }}>{percentage}% of spend</div>
    </div>
  )
}

export function DonutChart({ data }: DonutChartProps) {
  if (!data || data.length === 0) {
    return (
      <div style={{ height: 220, display: 'grid', placeItems: 'center', color: '#6d7588', fontSize: 12 }}>
        No categorized spending data yet
      </div>
    )
  }

  const chartData = data.slice(0, 6).map((item) => ({
    name: item.category,
    value: item.total,
    color: getCategoryHexColor(item.category),
    percentage: item.percentage,
  }))

  const total = chartData.reduce((acc, curr) => acc + curr.value, 0)

  return (
    <div style={{ display: 'flex', alignItems: 'center', gap: 24, height: 230 }}>
      <div style={{ width: 170, height: 170, position: 'relative' }}>
        <ResponsiveContainer width="100%" height="100%">
          <PieChart>
            <Pie
              data={chartData}
              innerRadius={52}
              outerRadius={75}
              paddingAngle={3}
              dataKey="value"
            >
              {chartData.map((entry, index) => (
                <Cell key={`cell-${index}`} fill={entry.color} />
              ))}
            </Pie>
            <Tooltip content={<CustomTooltip />} />
          </PieChart>
        </ResponsiveContainer>
        <div
          style={{
            position: 'absolute',
            inset: 0,
            display: 'flex',
            flexDirection: 'column',
            justifyContent: 'center',
            alignItems: 'center',
            pointerEvents: 'none',
          }}
        >
          <strong style={{ fontSize: 14, fontWeight: 700 }}>{formatINR(total)}</strong>
          <span style={{ fontSize: 9, color: 'var(--muted)' }}>Top Spend</span>
        </div>
      </div>

      <div style={{ flex: 1, display: 'flex', flexDirection: 'column', gap: 8, maxHeight: 200, overflowY: 'auto' }}>
        {chartData.map((item) => (
          <div
            key={item.name}
            style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', fontSize: 11 }}
          >
            <span style={{ display: 'flex', alignItems: 'center', gap: 6, color: 'var(--ink)' }}>
              <i style={{ width: 8, height: 8, borderRadius: 2, background: item.color, display: 'inline-block' }} />
              {item.name}
            </span>
            <div style={{ textAlign: 'right' }}>
              <b style={{ display: 'block', fontSize: 11 }}>{formatINR(item.value)}</b>
              <small style={{ color: 'var(--muted)', fontSize: 9 }}>{item.percentage}%</small>
            </div>
          </div>
        ))}
      </div>
    </div>
  )
}
