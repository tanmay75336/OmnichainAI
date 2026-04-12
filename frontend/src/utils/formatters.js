export function formatCurrency(value) {
  if (value == null || Number.isNaN(Number(value))) {
    return 'N/A'
  }

  return new Intl.NumberFormat('en-IN', {
    style: 'currency',
    currency: 'INR',
    maximumFractionDigits: 0,
  }).format(Number(value))
}

export function formatNumber(value, digits = 1) {
  if (value == null || Number.isNaN(Number(value))) {
    return 'N/A'
  }

  return Number(value).toFixed(digits)
}

export function formatPercent(value) {
  if (value == null || Number.isNaN(Number(value))) {
    return 'N/A'
  }

  return `${Math.round(Number(value))}%`
}

export function sentenceCase(value) {
  if (!value) {
    return 'N/A'
  }

  return value.charAt(0).toUpperCase() + value.slice(1)
}

export function titleCase(value) {
  if (!value) {
    return 'N/A'
  }

  return value
    .replace(/_/g, ' ')
    .split(' ')
    .filter(Boolean)
    .map((part) => part.charAt(0).toUpperCase() + part.slice(1))
    .join(' ')
}

export function formatDateLabel(value) {
  if (!value) {
    return 'Not selected'
  }

  const date = new Date(`${value}T00:00:00`)
  if (Number.isNaN(date.getTime())) {
    return value
  }

  return date.toLocaleDateString('en-IN', {
    day: '2-digit',
    month: 'short',
    year: 'numeric',
  })
}

export function toLatLng(coordinates) {
  if (!Array.isArray(coordinates) || coordinates.length < 2) {
    return null
  }

  return [coordinates[1], coordinates[0]]
}

export function clamp(value, min, max) {
  return Math.min(max, Math.max(min, value))
}

export function buildMetricTone(value) {
  const normalized = String(value || '').toLowerCase()
  if (normalized.includes('high') || normalized.includes('critical')) {
    return 'danger'
  }
  if (normalized.includes('medium') || normalized.includes('warning') || normalized.includes('risky')) {
    return 'warning'
  }
  return 'normal'
}
