import SectionCard from './SectionCard'
import StatusPill from './StatusPill'
import {
  formatCurrency,
  formatPercent,
  formatNumber,
  titleCase,
} from '../utils/formatters'

const TRANSPORT_OPTIONS = [
  { value: 'road', label: 'Road' },
  { value: 'rail', label: 'Rail' },
  { value: 'air', label: 'Air' },
  { value: 'waterways', label: 'Waterways' },
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
  const regionContext = routeData?.region_context
  const cargoProfile = routeData?.cargo_profile
  const shipmentPricing = routeData?.shipment_pricing

  const handleChange = (event) => {
    const { name, value } = event.target
    onFormChange((current) => ({ ...current, [name]: value }))
  }

  const handleCargoChange = (event) => {
    const { name, value } = event.target
    onFormChange((current) => ({
      ...current,
      cargo: {
        ...current.cargo,
        [name]: value,
      },
    }))
  }

  const handleDimensionChange = (event) => {
    const { name, value } = event.target
    onFormChange((current) => ({
      ...current,
      cargo: {
        ...current.cargo,
        dimensions_cm: {
          ...current.cargo.dimensions_cm,
          [name]: value,
        },
      },
    }))
  }

  const handleSubmit = (event) => {
    event.preventDefault()
    onSubmit()
  }

  return (
    <SectionCard
      title="Route Input + Shipment Analysis"
      subtitle="Full delivery address, auto tier detection, load-aware quoting"
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
        <form className="analysis-form analysis-form--route" onSubmit={handleSubmit}>
          <label className="field field--wide">
            <span>Pickup address</span>
            <textarea
              name="source"
              value={form.source}
              onChange={handleChange}
              placeholder="Warehouse / pickup address with area, city, state, pincode"
              rows={3}
            />
          </label>

          <label className="field field--wide">
            <span>Delivery address</span>
            <textarea
              name="destination"
              value={form.destination}
              onChange={handleChange}
              placeholder="Shop / building / area / city / state / pincode"
              rows={3}
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
            <span>Total weight (kg)</span>
            <input
              name="weight_kg"
              value={form.cargo.weight_kg}
              onChange={handleCargoChange}
              placeholder="120"
              inputMode="decimal"
            />
          </label>

          <label className="field">
            <span>Quantity</span>
            <input
              name="quantity"
              value={form.cargo.quantity}
              onChange={handleCargoChange}
              placeholder="24"
              inputMode="numeric"
            />
          </label>

          <label className="field">
            <span>Length (cm)</span>
            <input
              name="length"
              value={form.cargo.dimensions_cm.length}
              onChange={handleDimensionChange}
              placeholder="60"
              inputMode="decimal"
            />
          </label>

          <label className="field">
            <span>Width (cm)</span>
            <input
              name="width"
              value={form.cargo.dimensions_cm.width}
              onChange={handleDimensionChange}
              placeholder="45"
              inputMode="decimal"
            />
          </label>

          <label className="field">
            <span>Height (cm)</span>
            <input
              name="height"
              value={form.cargo.dimensions_cm.height}
              onChange={handleDimensionChange}
              placeholder="35"
              inputMode="decimal"
            />
          </label>

          <button className="primary-button" type="submit" disabled={loading}>
            {loading ? 'Analyzing corridor...' : 'Analyze Route'}
          </button>
        </form>

        <div className="report-note">
          Region tier now auto-detects from the delivery address. Gemini assists when available, with a deterministic fallback if AI is unavailable.
        </div>

        {error ? <div className="inline-banner inline-banner--danger">{error}</div> : null}

        <div className="analysis-report">
          {selectedRoute ? (
            <>
              <div className="metric-grid">
                <div className="metric-box">
                  <span>ETA</span>
                  <strong>{selectedRoute.duration_text}</strong>
                </div>
                <div className="metric-box">
                  <span>Shipment quote</span>
                  <strong>{formatCurrency(shipmentPricing?.selected_estimate_inr)}</strong>
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
                  <h3>Delivery context</h3>
                  <dl className="report-list">
                    <div>
                      <dt>Pickup node</dt>
                      <dd>{selectedRoute.source_details?.label || selectedRoute.source}</dd>
                    </div>
                    <div>
                      <dt>Delivery node</dt>
                      <dd>{selectedRoute.destination_details?.label || selectedRoute.destination}</dd>
                    </div>
                    <div>
                      <dt>Auto region tier</dt>
                      <dd>{titleCase(routeData.region_type)}</dd>
                    </div>
                    <div>
                      <dt>Tier confidence</dt>
                      <dd>{formatPercent((regionContext?.confidence || 0) * 100)}</dd>
                    </div>
                    <div>
                      <dt>Billable weight</dt>
                      <dd>{formatNumber(cargoProfile?.billable_weight_kg, 1)} kg</dd>
                    </div>
                    <div>
                      <dt>Volumetric weight</dt>
                      <dd>{formatNumber(cargoProfile?.volumetric_weight_kg, 1)} kg</dd>
                    </div>
                  </dl>
                </div>

                <div className="report-block">
                  <h3>Shipment quote snapshot</h3>
                  <dl className="report-list">
                    <div>
                      <dt>Benchmark range</dt>
                      <dd>
                        {formatCurrency(shipmentPricing?.estimated_range_inr?.min)}
                        {' - '}
                        {formatCurrency(shipmentPricing?.estimated_range_inr?.max)}
                      </dd>
                    </div>
                    <div>
                      <dt>Fuel component</dt>
                      <dd>{formatCurrency(shipmentPricing?.fuel_cost_inr)}</dd>
                    </div>
                    <div>
                      <dt>Taxes</dt>
                      <dd>{formatCurrency(shipmentPricing?.taxes_inr)}</dd>
                    </div>
                    <div>
                      <dt>Current mode</dt>
                      <dd>{selectedRoute.transport_profile?.label}</dd>
                    </div>
                    <div>
                      <dt>Suggested mode</dt>
                      <dd>{recommendation?.label}</dd>
                    </div>
                    <div>
                      <dt>Traffic advisory</dt>
                      <dd>{titleCase(selectedRoute.traffic_analysis?.status)}</dd>
                    </div>
                  </dl>
                  <div className="report-note">{selectedRoute.traffic_analysis?.advisory}</div>
                </div>
              </div>

              <div className="report-grid">
                <div className="report-block">
                  <h3>Decision summary</h3>
                  <p className="report-copy">{routeData.decision_support?.executive_summary}</p>
                  <div className="report-note">{regionContext?.reason}</div>
                </div>

                <div className="report-block">
                  <h3>Quote assumptions</h3>
                  <ul className="bullet-list">
                    {shipmentPricing?.assumptions?.map((item) => (
                      <li key={item}>{item}</li>
                    ))}
                  </ul>
                </div>
              </div>
            </>
          ) : (
            <div className="empty-state">
              Enter pickup and delivery addresses with the shipment load details to generate route directions, alternate traffic options, and shipment cost estimates.
            </div>
          )}
        </div>
      </div>
    </SectionCard>
  )
}
