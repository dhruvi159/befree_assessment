import { describe, it, expect } from 'vitest'
import { formatINR, formatDate, getCategoryColor, methodLabel } from '../utils/format'

describe('Formatting Utilities', () => {
  it('formats INR numbers correctly with Indian grouping', () => {
    expect(formatINR(123456.78)).toBe('₹1,23,456.78')
    expect(formatINR(1000)).toBe('₹1,000.00')
    expect(formatINR(85000)).toBe('₹85,000.00')
    expect(formatINR(-2450.5)).toBe('-₹2,450.50')
    expect(formatINR(0)).toBe('₹0.00')
    expect(formatINR(null)).toBe('—')
  })

  it('formats date strings', () => {
    expect(formatDate('2025-06-15')).toContain('2025')
    expect(formatDate(null)).toBe('—')
  })

  it('maps category colors and method labels', () => {
    expect(getCategoryColor('Food & Dining')).toBe('orange')
    expect(getCategoryColor('Salary & Income')).toBe('green')
    expect(methodLabel('rule_based')).toBe('Rule')
    expect(methodLabel('machine_learning')).toBe('ML')
  })
})

