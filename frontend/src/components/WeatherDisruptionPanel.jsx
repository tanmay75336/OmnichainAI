import SectionCard from './SectionCard'
import { formatDateLabel, formatNumber } from '../utils/formatters'

export default function WeatherDisruptionPanel({
  shipmentDate,
  onShipmentDateChange,
  signals,
  selectedDisruptionId,
  onSelectedDisruptionIdChange,
  onSimulate,
  simulationLoading,
  simulationResult,
  simulationError,
  routeData,
}) {
  const weather = routeData?.weather

  return (
    <SectionCard
      title="Weather + Disruption Intelligence"
      subtitle="Shipment date, alerting, simulation"
      aside={<span className="section-card__hint">{formatDateLabel(shipmentDate)}</span>}
    >
      <div className="weather-panel">
        <div className="weather-controls">
          <label className="field">
            <span>Shipment date</span>
            <input
              type="date"
              value={shipmentDate}
              onChange={(event) => onShipmentDateChange(event.target.value)}
            />
          </label>

          <label className="field">
            <span>Scenario to model</span>
            <select
              value={selectedDisruptionId}
              onChange={(event) => onSelectedDisruptionIdChange(event.target.value)}
              disabled={!routeData}
            >
              <option value="monsoon">Monsoon</option>
              <option value="flood">Flood</option>
              <option value="political">Political / strike</option>
              <option value="holiday">Holiday congestion</option>
            </select>
          </label>

          <button
            type="button"
            className="primary-button"
            disabled={!routeData || simulationLoading}
            onClick={onSimulate}
          >
            {simulationLoading ? 'Running simulation...' : 'Run Disruption Scenario'}
          </button>
        </div>

        {weather ? (
          <div className="weather-summary-strip">
            <div>
              <span>Condition</span>
              <strong>{weather.condition}</strong>
            </div>
            <div>
              <span>Rainfall</span>
              <strong>{formatNumber(weather.rainfall_mm, 1)} mm</strong>
            </div>
            <div>
              <span>Visibility</span>
              <strong>{formatNumber(weather.visibility_km, 1)} km</strong>
            </div>
            <div>
              <span>Feed source</span>
              <strong>{weather.api_source}</strong>
            </div>
          </div>
        ) : null}

        <div className="alert-stack">
          {signals.length ? (
            signals.map((signal) => (
              <article key={signal.id} className={`alert-card alert-card--${signal.severity}`}>
                <strong>{signal.label}</strong>
                <p>{signal.reason}</p>
                <small>{signal.backendMapping}</small>
              </article>
            ))
          ) : (
            <div className="empty-state">
              Analyze a route first. Weather-based disruption detection will appear here.
            </div>
          )}
        </div>

        {simulationError ? (
          <div className="inline-banner inline-banner--danger">{simulationError}</div>
        ) : null}

        {simulationResult ? (
          <div className="simulation-summary">
            <div className="metric-grid metric-grid--compact">
              <div className="metric-box">
                <span>Delay</span>
                <strong>{simulationResult.delay_percentage}%</strong>
              </div>
              <div className="metric-box">
                <span>Cost increase</span>
                <strong>{simulationResult.cost_increase_percentage}%</strong>
              </div>
              <div className="metric-box">
                <span>Risk change</span>
                <strong>{simulationResult.risk_change}</strong>
              </div>
            </div>
            <p className="report-copy">{simulationResult.summary}</p>
            <div className="report-note">
              {simulationResult.scenario_modeling_note || 'Disruption mapping executed through the backend simulation engine.'}
            </div>
          </div>
        ) : null}
      </div>
    </SectionCard>
  )
}
