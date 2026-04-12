import { clamp, formatDateLabel, toLatLng } from './formatters'

function buildShipmentId(routeData, shipmentDate) {
  const sourceCode = (routeData?.route?.source || 'SRC').slice(0, 3).toUpperCase()
  const destinationCode = (routeData?.route?.destination || 'DST')
    .slice(0, 3)
    .toUpperCase()
  const dateCode = (shipmentDate || new Date().toISOString().slice(0, 10)).replaceAll('-', '')
  return `OMNI-${sourceCode}-${destinationCode}-${dateCode}`
}

function interpolateCoordinates(start, end, progress) {
  if (!start || !end) {
    return null
  }

  return [
    start[0] + (end[0] - start[0]) * progress,
    start[1] + (end[1] - start[1]) * progress,
  ]
}

function buildTimeline(routeData, shipmentDate, progress, liveLocation) {
  const route = routeData.route
  const routeStages = routeData.decision_support?.route_stages || []

  return [
    {
      id: 'dispatch',
      label: 'Origin dispatch',
      status: 'completed',
      location: route.source,
      timestamp: `${formatDateLabel(shipmentDate)} 08:30`,
      detail: routeStages[0]?.detail || `Shipment released from ${route.source}.`,
    },
    {
      id: 'linehaul',
      label: 'Primary corridor',
      status: progress >= 0.42 ? 'completed' : 'active',
      location: `${Math.round(route.distance_km * Math.min(progress, 0.55))} km from origin`,
      timestamp: `${formatDateLabel(shipmentDate)} 12:45`,
      detail: routeStages[1]?.detail || 'Line-haul leg progressing through trunk corridor.',
    },
    {
      id: 'monitoring',
      label: 'Live tracking window',
      status: progress >= 0.65 ? 'completed' : 'active',
      location: liveLocation?.label || 'In transit',
      timestamp: `${formatDateLabel(shipmentDate)} 15:10`,
      detail:
        routeData.route.congestion_index >= 0.55
          ? 'Traffic pressure detected on the next corridor section. Keep alternate mode or node fallback ready.'
          : 'Movement continues within expected operating envelope.',
    },
    {
      id: 'destination',
      label: 'Destination handoff',
      status: progress >= 1 ? 'completed' : 'planned',
      location: route.destination,
      timestamp: `${formatDateLabel(shipmentDate)} 18:30`,
      detail: routeStages[3]?.detail || `Final delivery planned at ${route.destination}.`,
    },
  ]
}

export function buildShipmentRecord(routeData, shipmentDate) {
  if (!routeData?.route?.source_coordinates || !routeData?.route?.destination_coordinates) {
    return null
  }

  const route = routeData.route
  const risk = routeData.risk || {}
  const suggestion = routeData.suggested_transport_mode || {}
  const progress = clamp(0.34 + (100 - (risk.weighted_score_pct || 40)) / 180, 0.24, 0.86)
  const liveCoordinates = interpolateCoordinates(
    route.source_coordinates,
    route.destination_coordinates,
    progress
  )
  const distanceCoveredKm = Math.round((route.distance_km || 0) * progress)
  const shipmentId = buildShipmentId(routeData, shipmentDate)
  const liveLocation = {
    coordinates: liveCoordinates,
    label: `${distanceCoveredKm} km covered`,
    eta: route.duration_text,
  }

  return {
    shipmentId,
    source: route.source,
    destination: route.destination,
    progress,
    progressLabel: `${Math.round(progress * 100)}%`,
    currentStatus:
      progress >= 0.75
        ? 'Approaching destination'
        : progress >= 0.42
          ? 'Line-haul in progress'
          : 'Origin release complete',
    currentLocation: liveLocation,
    alternateAction:
      suggestion.mode && suggestion.mode !== route.transport_mode
        ? suggestion.rationale
        : 'Current transport mode remains acceptable; continue monitoring.',
    timeline: buildTimeline(routeData, shipmentDate, progress, liveLocation),
    routeLine: [toLatLng(route.source_coordinates), toLatLng(route.destination_coordinates)].filter(Boolean),
    routeMode: route.transport_mode,
  }
}

export function findShipmentRecord(shipmentId, shipmentRecord) {
  if (!shipmentId || !shipmentRecord) {
    return null
  }

  return shipmentId.trim().toUpperCase() === shipmentRecord.shipmentId.toUpperCase()
    ? shipmentRecord
    : null
}

export function buildTrackingQrValue(record) {
  if (!record) {
    return ''
  }

  return JSON.stringify({
    shipmentId: record.shipmentId,
    source: record.source,
    destination: record.destination,
    status: record.currentStatus,
    progress: record.progressLabel,
  })
}
