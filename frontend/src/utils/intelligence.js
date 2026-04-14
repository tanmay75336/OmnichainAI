import { DISRUPTION_CATALOG } from '../services/api'
import { clamp } from './formatters'

const MONSOON_MONTHS = new Set([6, 7, 8, 9])

export function getTodayDateString() {
  return new Date().toISOString().split('T')[0]
}

function getMonthNumber(dateString) {
  if (!dateString) {
    return null
  }

  const date = new Date(`${dateString}T00:00:00`)
  if (Number.isNaN(date.getTime())) {
    return null
  }

  return date.getMonth() + 1
}

function isSunday(dateString) {
  if (!dateString) {
    return false
  }

  const date = new Date(`${dateString}T00:00:00`)
  return date.getDay() === 0
}

export function deriveDisruptionSignals({ routeData, shipmentDate }) {
  if (!routeData) {
    return []
  }

  const weather = routeData.weather || {}
  const regionType = routeData.region_type
  const month = getMonthNumber(shipmentDate)
  const signals = []

  if (month && MONSOON_MONTHS.has(month)) {
    signals.push({
      ...DISRUPTION_CATALOG.monsoon,
      reason:
        'Selected dispatch date falls inside the monsoon operating window for India.',
    })
  }

  if ((weather.rainfall_mm || 0) >= 15 || weather.condition === 'thunderstorm') {
    signals.push({
      ...DISRUPTION_CATALOG.flood,
      reason:
        'Current weather feed shows rainfall or storm conditions that can escalate into corridor flooding.',
    })
  }

  if (regionType === 'sez') {
    signals.push({
      ...DISRUPTION_CATALOG.political,
      severity: 'medium',
      reason:
        'SEZ movements depend on compliance windows and can degrade quickly under strike or operational restrictions.',
    })
  }

  if (isSunday(shipmentDate)) {
    signals.push({
      ...DISRUPTION_CATALOG.holiday,
      reason:
        'Dispatch date lands on a Sunday, so holiday-like staffing and gate congestion should be planned for.',
    })
  }

  const deduped = new Map()
  signals.forEach((signal) => {
    if (!deduped.has(signal.id)) {
      deduped.set(signal.id, signal)
    }
  })

  return Array.from(deduped.values())
}

export function buildWeatherTrend(weather, shipmentDate) {
  const month = getMonthNumber(shipmentDate)
  const baseScore = clamp(Math.round((weather?.weather_risk_score || 0.2) * 100), 10, 95)
  const monsoonBias = month && MONSOON_MONTHS.has(month) ? 12 : 0
  const rainfallBias = Math.min(18, Math.round(weather?.rainfall_mm || 0))

  return Array.from({ length: 6 }, (_, index) => {
    const drift = index * 4 - 8
    const level = clamp(baseScore + monsoonBias + rainfallBias + drift, 8, 96)
    return {
      label: `${index * 4}h`,
      level,
    }
  })
}

export function buildOperationalAlerts({
  routeData,
  shipmentDate,
  simulationResult,
  newsState,
}) {
  if (!routeData) {
    return []
  }

  const items = []
  const signals = deriveDisruptionSignals({ routeData, shipmentDate })
  const intelligence = routeData.intelligence || {}
  const weakPoints = intelligence.weak_points || []
  const traffic = routeData.route?.traffic_analysis

  intelligence.alerts?.forEach((alert) => {
    items.push({
      title: alert,
      tone: 'warning',
      source: 'System alert',
    })
  })

  signals.forEach((signal) => {
    items.push({
      title: signal.label,
      detail: signal.reason,
      tone: signal.severity === 'high' ? 'danger' : 'warning',
      source: 'Disruption mapping',
    })
  })

  weakPoints.forEach((point) => {
    items.push({
      title: point,
      tone: 'normal',
      source: 'Weak point',
    })
  })

  if (traffic?.projected_delay_minutes > 0) {
    items.push({
      title: `${traffic.projected_delay_minutes} min projected traffic delay`,
      detail: traffic.advisory,
      tone: traffic.projected_delay_minutes >= 15 ? 'danger' : 'warning',
      source: 'Traffic model',
    })
  }

  if (simulationResult?.summary) {
    items.push({
      title: simulationResult.summary,
      detail: simulationResult.recommendation,
      tone: 'danger',
      source: 'Scenario simulation',
    })
  }

  newsState?.items?.forEach((item) => {
    items.push({
      title: item.headline,
      detail: item.recommended_action,
      tone: item.impact === 'high' ? 'danger' : item.impact === 'medium' ? 'warning' : 'normal',
      source: `${item.tag || 'Gemini'} feed`,
    })
  })

  return items.slice(0, 8)
}
