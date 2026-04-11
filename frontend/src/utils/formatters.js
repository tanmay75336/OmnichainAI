export function formatCurrencyInr(value) {
  if (value == null || Number.isNaN(Number(value))) return '--'
  return `Rs. ${Number(value).toLocaleString('en-IN', { maximumFractionDigits: 0 })}`
}

export function formatPercent(value, { signed = false } = {}) {
  if (value == null || Number.isNaN(Number(value))) return '--'
  const num = Number(value)
  return `${signed && num > 0 ? '+' : ''}${num.toFixed(num % 1 === 0 ? 0 : 1)}%`
}

export function formatRiskScore(value) {
  if (value == null || Number.isNaN(Number(value))) return '--'
  return `${Number(value).toFixed(0)} / 100`
}

export function formatReliability(value) {
  if (value == null || Number.isNaN(Number(value))) return '--'
  return `${Number(value).toFixed(0)} / 100`
}

export function displayModeLabel(mode) {
  if (!mode) return '--'
  const labels = {
    road: 'Road',
    rail: 'Rail',
    air: 'Air',
    waterways: 'Waterways',
  }
  return labels[mode] || mode
}

export function levelFromRiskLabel(label) {
  if (!label) return 'info'
  const normalized = String(label).toLowerCase()
  if (normalized === 'low' || normalized === 'normal') return 'normal'
  if (normalized === 'medium' || normalized === 'warning' || normalized === 'risky') return 'warning'
  if (normalized === 'high' || normalized === 'critical') return 'critical'
  return 'info'
}

export function titleCase(value) {
  if (!value) return '--'
  return String(value)
    .replace(/_/g, ' ')
    .split(' ')
    .filter(Boolean)
    .map((part) => part.charAt(0).toUpperCase() + part.slice(1))
    .join(' ')
}
