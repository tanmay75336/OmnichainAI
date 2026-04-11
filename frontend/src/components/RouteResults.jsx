import React from 'react'
import StatusBadge from './StatusBadge'
import {
  displayModeLabel,
  formatCurrencyInr,
  formatReliability,
  formatRiskScore,
  levelFromRiskLabel,
  titleCase,
} from '../utils/formatters'
import './RouteResults.css'

function safeText(value, fallback = '--') {
  return value != null && value !== '' ? value : fallback
}

export default function RouteResults({ data, loading, error }) {
  if (loading) {
    return (
      <section className="route-results panel">
        <div className="panel__header">
          <span className="panel__header-label">02</span>
          <h2 className="panel__title">Route Analysis Results</h2>
        </div>
        <div className="route-results__placeholder">
          <span style={{ color: 'var(--text-muted)' }}>Running route analysis...</span>
        </div>
      </section>
    )
  }

  if (error) {
    return (
      <section className="route-results panel">
        <div className="panel__header">
          <span className="panel__header-label">02</span>
          <h2 className="panel__title">Route Analysis Results</h2>
        </div>
        <div className="route-results__placeholder">
          <div className="error-inline" style={{ maxWidth: 480 }}>{error}</div>
        </div>
      </section>
    )
  }

  if (!data) {
    return (
      <section className="route-results panel">
        <div className="panel__header">
          <span className="panel__header-label">02</span>
          <h2 className="panel__title">Route Analysis Results</h2>
        </div>
        <div className="route-results__placeholder">
          <p className="placeholder-text">Run a route query to load distance, time, cost, risk, and transport options.</p>
        </div>
      </section>
    )
  }

  const {
    route = {},
    weather = {},
    risk = {},
    region_type,
    suggested_transport_mode: suggestedMode,
    modal_options: modalOptions = [],
    decision_support: decisionSupport = {},
  } = data

  const riskLevel = levelFromRiskLabel(risk?.overall_risk)
  const weatherRiskLevel = levelFromRiskLabel(
    weather?.weather_risk_score >= 0.65 ? 'High' : weather?.weather_risk_score >= 0.35 ? 'Medium' : 'Low'
  )

  return (
    <section className="route-results panel">
      <div className="panel__header">
        <span className="panel__header-label">02</span>
        <h2 className="panel__title">Route Analysis Results</h2>
        <div style={{ marginLeft: 'auto' }}>
          <StatusBadge
            level={riskLevel}
            label={`Risk: ${risk?.overall_risk || 'Unknown'}`}
          />
        </div>
      </div>

      <div className="route-results__body">
        <div className="metrics-grid metrics-grid--seven">
          <div className="metric-cell">
            <span className="metric-label">Distance</span>
            <span className="metric-value mono">{safeText(route.distance_text)}</span>
          </div>
          <div className="metric-cell">
            <span className="metric-label">Est. Time</span>
            <span className="metric-value mono">{safeText(route.duration_text)}</span>
          </div>
          <div className="metric-cell">
            <span className="metric-label">Est. Cost</span>
            <span className="metric-value mono">{formatCurrencyInr(route.estimated_cost_inr)}</span>
          </div>
          <div className="metric-cell">
            <span className="metric-label">Reliability Score</span>
            <span className="metric-value mono">{formatReliability(route.reliability_score_pct)}</span>
          </div>
          <div className="metric-cell">
            <span className="metric-label">Weighted Risk</span>
            <span className={`metric-value mono metric-value--${riskLevel}`}>
              {formatRiskScore(risk.weighted_score_pct)}
            </span>
          </div>
          <div className="metric-cell">
            <span className="metric-label">Region</span>
            <span className="metric-value">
              <span className="tag tag--neutral">{titleCase(region_type)}</span>
            </span>
          </div>
          <div className="metric-cell">
            <span className="metric-label">Suggested Mode</span>
            <span className="metric-value">{safeText(suggestedMode?.label)}</span>
          </div>
        </div>

        <hr className="divider" />

        <div className="results-columns">
          <div className="results-col">
            <p className="section-label">Risk Breakdown</p>
            <table className="data-table">
              <tbody>
                <tr>
                  <td className="dt-key">Risk Level</td>
                  <td className="dt-val">
                    <span className={`tag tag--${riskLevel}`}>{risk?.overall_risk || 'Unknown'}</span>
                  </td>
                </tr>
                <tr>
                  <td className="dt-key">Infrastructure Impact</td>
                  <td className="dt-val">{safeText(risk?.factors?.infrastructure?.impact)}</td>
                </tr>
                <tr>
                  <td className="dt-key">Transport Reliability</td>
                  <td className="dt-val mono">{safeText(risk?.factors?.transport?.impact)}</td>
                </tr>
                <tr>
                  <td className="dt-key">Congestion Index</td>
                  <td className="dt-val mono">
                    {risk?.congestion_index != null ? formatRiskScore(risk.congestion_index * 100) : '--'}
                  </td>
                </tr>
              </tbody>
            </table>
          </div>

          <div className="results-col">
            <p className="section-label">Weather Impact</p>
            <table className="data-table">
              <tbody>
                <tr>
                  <td className="dt-key">Condition</td>
                  <td className="dt-val">{safeText(titleCase(weather.condition))}</td>
                </tr>
                <tr>
                  <td className="dt-key">Rainfall</td>
                  <td className="dt-val mono">
                    {weather.rainfall_mm != null ? `${weather.rainfall_mm} mm` : '--'}
                  </td>
                </tr>
                <tr>
                  <td className="dt-key">Visibility</td>
                  <td className="dt-val mono">
                    {weather.visibility_km != null ? `${weather.visibility_km} km` : '--'}
                  </td>
                </tr>
                <tr>
                  <td className="dt-key">Weather Risk</td>
                  <td className="dt-val">
                    <span className={`tag tag--${weatherRiskLevel}`}>
                      {safeText(titleCase(weather.weather_risk_label), 'Stable')}
                    </span>
                  </td>
                </tr>
              </tbody>
            </table>
          </div>
        </div>

        <hr className="divider" />

        <div className="route-summary-grid">
          <div className="route-summary-card">
            <p className="section-label">Operational Summary</p>
            <table className="data-table">
              <tbody>
                <tr>
                  <td className="dt-key">Source</td>
                  <td className="dt-val">{safeText(route.source)}</td>
                </tr>
                <tr>
                  <td className="dt-key">Destination</td>
                  <td className="dt-val">{safeText(route.destination)}</td>
                </tr>
                <tr>
                  <td className="dt-key">Selected Mode</td>
                  <td className="dt-val">{displayModeLabel(route.transport_mode)}</td>
                </tr>
                <tr>
                  <td className="dt-key">Suggested Mode</td>
                  <td className="dt-val">{safeText(suggestedMode?.label)}</td>
                </tr>
              </tbody>
            </table>
          </div>

          <div className="route-summary-card">
            <p className="section-label">Multi-Modal Comparison</p>
            <div className="mode-comparison">
              {modalOptions.map((option) => (
                <div
                  key={option.mode}
                  className={`mode-row ${option.is_recommended ? 'mode-row--recommended' : ''}`}
                >
                  <div className="mode-row__primary">
                    <span className="mode-row__mode">{option.label}</span>
                    {option.is_recommended && <span className="tag tag--normal">Recommended</span>}
                  </div>
                  <div className="mode-row__metrics">
                    <span>{option.duration_text}</span>
                    <span>{formatCurrencyInr(option.estimated_cost_inr)}</span>
                    <span>{option.weighted_score_pct}/100</span>
                    <span>{option.overall_risk}</span>
                  </div>
                </div>
              ))}
            </div>
          </div>
        </div>

        {risk?.recommendation && (
          <>
            <hr className="divider" />
            <div className="recommendation-box">
              <span className="section-label" style={{ marginBottom: 4 }}>System Recommendation</span>
              <p className="recommendation-text">{risk.recommendation}</p>
              {suggestedMode?.rationale && (
                <p className="recommendation-text recommendation-text--secondary">{suggestedMode.rationale}</p>
              )}
            </div>
          </>
        )}

        {decisionSupport?.executive_summary && (
          <>
            <hr className="divider" />
            <div className="route-decision-grid">
              <div className="route-summary-card">
                <p className="section-label">Executive Summary</p>
                <p className="route-decision-text">{decisionSupport.executive_summary}</p>
                <hr className="divider" />
                <p className="section-label">Distribution Model</p>
                <p className="route-decision-text">
                  <strong>{decisionSupport.distribution_model?.model}</strong><br />
                  {decisionSupport.distribution_model?.description}
                </p>
              </div>

              <div className="route-summary-card">
                <p className="section-label">Tier / SEZ Strategy</p>
                <div className="route-strategy-stack">
                  <div>
                    <span className="route-strategy-label">Last-Mile Strategy</span>
                    <p className="route-decision-text">{decisionSupport.last_mile_strategy}</p>
                  </div>
                  <div>
                    <span className="route-strategy-label">SEZ / Compliance Strategy</span>
                    <p className="route-decision-text">{decisionSupport.sez_strategy}</p>
                  </div>
                </div>
              </div>

              <div className="route-summary-card">
                <p className="section-label">Operational Stages</p>
                <div className="route-stage-list">
                  {(decisionSupport.route_stages || []).map((stage) => (
                    <div key={stage.stage} className="route-stage-item">
                      <span className="route-stage-title">{stage.stage}</span>
                      <span className="route-stage-detail">{stage.detail}</span>
                    </div>
                  ))}
                </div>
              </div>

              <div className="route-summary-card">
                <p className="section-label">Action Items</p>
                <ul className="route-action-list">
                  {(decisionSupport.action_items || []).map((item, index) => (
                    <li key={`${item}-${index}`}>{item}</li>
                  ))}
                </ul>
              </div>
            </div>
          </>
        )}
      </div>
    </section>
  )
}
