/** Format a number as Indian Rupee (INR) */
export function formatINR(amount: number | null | undefined): string {
  if (amount === null || amount === undefined) return '\u2014'
  const isNegative = amount < 0
  const abs = Math.abs(amount)
  const formatted = abs.toFixed(2)
  const [intPart, decPart] = formatted.split('.')
  let result = ''
  if (intPart.length <= 3) {
    result = intPart
  } else {
    const last3 = intPart.slice(-3)
    const rest = intPart.slice(0, -3)
    const groups: string[] = []
    for (let i = rest.length; i > 0; i -= 2) {
      groups.unshift(rest.slice(Math.max(0, i - 2), i))
    }
    result = groups.join(',') + ',' + last3
  }
  return `${isNegative ? '-' : ''}\u20b9${result}.${decPart}`
}

/** Format YYYY-MM-DD to "04 Nov 2026" */
export function formatDate(date: string | null | undefined): string {
  if (!date) return '\u2014'
  try {
    const d = new Date(date + 'T00:00:00')
    return d.toLocaleDateString('en-IN', { day: '2-digit', month: 'short', year: 'numeric' })
  } catch {
    return date
  }
}

/** Format YYYY-MM to "Nov 2026" */
export function formatMonth(month: string): string {
  try {
    const [year, mon] = month.split('-')
    const d = new Date(parseInt(year), parseInt(mon) - 1, 1)
    return d.toLocaleDateString('en-IN', { month: 'short', year: 'numeric' })
  } catch {
    return month
  }
}

/** Map category name to a CSS color class */
export function getCategoryColor(category: string): string {
  const map: Record<string, string> = {
    'Food & Dining': 'orange',
    'Transportation': 'cyan',
    'Shopping': 'purple',
    'Entertainment': 'pink',
    'Utilities': 'blue',
    'Rent & Housing': 'indigo',
    'Healthcare': 'green',
    'Education': 'teal',
    'Salary & Income': 'green',
    'Transfers': 'gray',
    'Cash Withdrawal': 'red',
    'Cash Deposit': 'emerald',
    'Investments': 'violet',
    'Banking Charges': 'red',
    'Insurance': 'blue',
    'Taxes': 'amber',
    'Interest': 'lime',
    'Refunds & Reversals': 'emerald',
    'Friends & Family': 'pink',
    'Uncategorized': 'neutral',
  }
  return map[category] || 'gray'
}

/** Map category to chart hex color */
export function getCategoryHexColor(category: string): string {
  const map: Record<string, string> = {
    'Food & Dining': '#f59e0b',
    'Transportation': '#06b6d4',
    'Shopping': '#8b5cf6',
    'Entertainment': '#ec4899',
    'Utilities': '#3b82f6',
    'Rent & Housing': '#6366f1',
    'Healthcare': '#10b981',
    'Education': '#14b8a6',
    'Salary & Income': '#22c55e',
    'Transfers': '#94a3b8',
    'Cash Withdrawal': '#ef4444',
    'Cash Deposit': '#34d399',
    'Investments': '#7c3aed',
    'Banking Charges': '#dc2626',
    'Insurance': '#2563eb',
    'Taxes': '#f59e0b',
    'Interest': '#84cc16',
    'Refunds & Reversals': '#10b981',
    'Friends & Family': '#f472b6',
    'Uncategorized': '#9ca3af',
  }
  return map[category] || '#9ca3af'
}

/** Return a confidence color based on score (0-1) */
export function getConfidenceColor(confidence: number): string {
  if (confidence >= 0.9) return '#18a67e'
  if (confidence >= 0.75) return '#4444db'
  return '#e8a528'
}

/** Classify transaction method display */
export function methodLabel(method: string): string {
  const labels: Record<string, string> = {
    rule_based: 'Rule',
    machine_learning: 'ML',
    manual: 'Manual',
    unclassified: 'None',
  }
  return labels[method] || method
}

/** Classify transaction method tone */
export function methodTone(method: string): string {
  const tones: Record<string, string> = {
    rule_based: 'blue',
    machine_learning: 'purple',
    manual: 'green',
    unclassified: 'neutral',
  }
  return tones[method] || 'neutral'
}

/** Human-readable file size */
export function formatFileSize(bytes: number): string {
  if (bytes < 1024) return `${bytes} B`
  if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`
  return `${(bytes / (1024 * 1024)).toFixed(1)} MB`
}