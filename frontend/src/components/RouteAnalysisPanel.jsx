import SectionCard from './SectionCard'
import StatusPill from './StatusPill'
import { formatCurrency, formatPercent } from '../utils/formatters'

const TRANSPORT_OPTIONS = [
  { value: 'road', label: 'Road' },
  { value: 'rail', label: 'Rail' },
  { value: 'air', label: 'Air' },
  { value: 'waterways', label: 'Waterways' },
]

const REGION_OPTIONS = [
  { value: 'tier_2', label: 'Tier-2' },
  { value: 'tier_3', label: 'Tier-3' },
  { value: 'sez', label: 'SEZ' },
]

function getRiskTone(riskLabel) {
  if (riskLabel === 'High') {
    return 'danger'
  }
  if (riskLabel === 'Medium') {
    return 'warning'
  }
  return 'success'
}

export default function RouteAnalysisPanel({
  form,
  onFormChange,
  onSubmit,
  loading,
  error,
  routeData,
  shipmentId,
}) {
  const selectedRoute = routeData?.route
  const risk = routeData?.risk
  const recommendation = routeData?.suggested_transport_mode

  const handleChange = (event) => {
    const { name, value } = event.target
    onFormChange((current) => ({ ...current, [name]: value }))
  }

  const handleSubmit = (event) => {
    event.preventDefault()
    onSubmit()
  }

  return (
    <SectionCard
      title="Route Input + Analysis"
      subtitle="Supplier route intelligence"
      aside={
        selectedRoute ? (
          <StatusPill
            label={risk?.overall_risk || 'Pending'}
            tone={getRiskTone(risk?.overall_risk)}
          />
        ) : null
      }
    >
      <div className="analysis-panel">
        <form className="analysis-form" onSubmit={handleSubmit}>
          <label className="field">
            <span>Source</span>
            <input
              name="source"
              value={form.source}
              onChange={handleChange}
              placeholder="Mumbai"
              autoComplete="off"
            />
          </label>

          <label className="field">
            <span>Destination</span>
            <input
              name="destination"
              value={form.destination}
              onChange={handleChange}
              placeholder="Pune"
              autoComplete="off"
            />
          </label>

          <label className="field">
            <span>Transport mode</span>
            <select name="transport_mode" value={form.transport_mode} onChange={handleChange}>
              {TRANSPORT_OPTIONS.map((option) => (
                <option key={option.value} value={option.value}>
                  {option.label}
                </option>
              ))}
            </select>
          </label>

          <label className="field">
            <span>Region</span>
            <select name="region_type" value={form.region_type} onChange={handleChange}>
              {REGION_OPTIONS.map((option) => (
                <option key={option.value} value={option.value}>
                  {option.label}
                </option>
              ))}
            </select>
          </label>

          <button className="primary-button" type="submit" disabled={loading}>
            {loading ? 'Analyzing corridor...' : 'Analyze Route'}
          </button>
        </form>

        {error ? <div className="inline-banner inline-banner--danger">{error}</div> : null}

        <div className="analysis-report">
          {selectedRoute ? (
            <>
              <div className="metric-grid">
                <div className="metric-box">
                  <span>Time</span>
                  <strong>{selectedRoute.duration_text}</strong>
                </div>
                <div className="metric-box">
                  <span>Cost</span>
                  <strong>{formatCurrency(selectedRoute.estimated_cost_inr)}</strong>
                </div>
                <div className="metric-box">
                  <span>Risk score</span>
                  <strong>{formatPercent(risk?.weighted_score_pct)}</strong>
                </div>
                <div className="metric-box">
                  <span>Tracking ID</span>
                  <strong>{shipmentId || 'Pending'}</strong>
                </div>
              </div>

              <div className="report-grid">
                <div className="report-block">
                  <h3>Selected route report</h3>
                  <dl className="report-list">
                    <div>
                      <dt>Corridor</dt>
                      <dd>
                        {selectedRoute.source}
                        {' -> '}
                        {selectedRoute.destination}
                      </dd>
                    </div>
                    <div>
                      <dt>Distance</dt>
                      <dd>{selectedRoute.distance_text}</dd>
                    </div>
                    <div>
                      <dt>Current mode</dt>
                      <dd>{selectedRoute.transport_profile?.label}</dd>
                    </div>
                    <div>
                      <dt>Suggested mode</dt>
                      <dd>{recommendation?.label}</dd>
                    </div>
                  </dl>
                </div>

                <div className="report-block">
                  <h3>Risk context</h3>
                  <p className="report-copy">{routeData.decision_support?.executive_summary}</p>
                  <div className="report-note">
                    {selectedRoute.is_fallback
                      ? 'Routing is currently using fallback distance logic instead of live ORS routing.'
                      : 'Routing is currently using live route data.'}
                  </div>
                </div>
              </div>
            </>
          ) : (
            <div className="empty-state">
              Enter a source, destination, transport mode, and region to generate the route intelligence report.
            </div>
          )}
        </div>
      </div>
    </SectionCard>
  )
}
