import StatusPill from './StatusPill'

function getStatusTone(status) {
  switch (status) {
    case 'online':
    case 'live':
    case 'configured':
      return 'success'
    case 'fallback':
    case 'degraded':
      return 'warning'
    case 'error':
    case 'offline':
    case 'missing':
      return 'danger'
    default:
      return 'neutral'
  }
}

function formatStatus(status) {
  switch (status) {
    case 'online':
      return 'Online'
    case 'offline':
      return 'Offline'
    case 'live':
      return 'Live API'
    case 'fallback':
      return 'Fallback'
    case 'configured':
      return 'Configured'
    case 'missing':
      return 'Key Missing'
    case 'error':
      return 'Error'
    default:
      return 'Checking'
  }
}

export default function TopBar({ serviceStatus, routeData, shipmentRecord }) {
  const route = routeData?.route
  const risk = routeData?.risk

  const statusItems = [
    { key: 'backend', label: 'Backend', value: serviceStatus.backend },
    { key: 'routing', label: 'OpenRouteService', value: serviceStatus.routing },
    { key: 'weather', label: 'OpenWeather', value: serviceStatus.weather },
    { key: 'gemini', label: 'Gemini', value: serviceStatus.gemini },
  ]

  return (
    <header className="topbar">
      <div className="topbar__identity">
        <div className="topbar__brand-mark">OC</div>
        <div>
          <p className="topbar__product">OmniChain AI</p>
          <h1 className="topbar__title">Smart Supply Chain Decision Intelligence System</h1>
        </div>
      </div>

      <div className="topbar__corridor">
        <p className="topbar__product">Active corridor</p>
        <div className="topbar__corridor-line">
          <strong>{route ? `${route.source} -> ${route.destination}` : 'Awaiting route analysis'}</strong>
          <span>
            {risk ? `${risk.overall_risk} risk / ${risk.weighted_score_pct}% score` : 'Run analysis to load route intelligence'}
          </span>
        </div>
        {shipmentRecord ? (
          <div className="topbar__shipment">Tracking ID: {shipmentRecord.shipmentId}</div>
        ) : null}
      </div>

      <div className="topbar__status-grid">
        {statusItems.map((item) => (
          <div key={item.key} className="topbar__status-item">
            <span>{item.label}</span>
            <StatusPill
              label={formatStatus(item.value)}
              tone={getStatusTone(item.value)}
            />
          </div>
        ))}
      </div>
    </header>
  )
}
