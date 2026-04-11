import React, { useState } from 'react'
import StatusBadge from './StatusBadge'
import {
  formatCurrencyInr,
  formatPercent,
  formatReliability,
  levelFromRiskLabel,
} from '../utils/formatters'
import './SimulationPanel.css'

const DISRUPTION_OPTIONS = [
  'Heavy rainfall in a region',
  'Port congestion or delays',
  'Increased demand in Tier-2 cities',
  'Route blockage due to regulatory or operational issues',
]

export default function SimulationPanel({ routeData, onSimulate, simResult, simLoading, simError }) {
  const [disruption, setDisruption] = useState('Monsoon')

  const hasRoute = Boolean(routeData?.route)
  const before = simResult?.before ?? {}
  const after = simResult?.after ?? {}

  const handleRun = () => {
    onSimulate({
      route: {
        source: routeData.route.source,
        destination: routeData.route.destination,
        transport_mode: routeData.route.transport_mode,
        region_type: routeData.region_type,
      },
      disruptionLabel: disruption,
    })
  }

  return (
    <section className="sim-panel panel">
      <div className="panel__header">
        <span className="panel__header-label">03</span>
        <h2 className="panel__title">Disruption Simulation</h2>
        {simResult && (
          <div style={{ marginLeft: 'auto' }}>
            <StatusBadge level="warning" label="Simulation Active" />
          </div>
        )}
      </div>

      <div className="sim-panel__body">
        <div className="sim-controls">
          <div className="form-group" style={{ flex: 1 }}>
            <label className="form-label">Disruption Scenario</label>
            <select
              className="form-select"
              value={disruption}
              onChange={(e) => setDisruption(e.target.value)}
              disabled={simLoading || !hasRoute}
            >
              {DISRUPTION_OPTIONS.map((option) => (
                <option key={option} value={option}>{option}</option>
              ))}
            </select>
          </div>
          <div className="form-group form-group--action">
            <label className="form-label">&nbsp;</label>
            <button
              className="btn-primary btn--orange"
              onClick={handleRun}
              disabled={simLoading || !hasRoute}
              title={!hasRoute ? 'Run a route analysis first' : ''}
            >
              {simLoading ? 'Simulating...' : 'Run Simulation'}
            </button>
          </div>
        </div>

        {!hasRoute && (
          <p className="sim-hint">Complete route analysis in Section 01 before running simulations.</p>
        )}

        {simError && <div className="error-inline">{simError}</div>}

        {simResult && (
          <div className="sim-results">
            {simResult.scenario_modeling_note && (
              <div className="sim-note">{simResult.scenario_modeling_note}</div>
            )}

            <hr className="divider" />

            <div className="sim-comparison">
              <div className="sim-col sim-col--before">
                <p className="section-label">Before Disruption</p>
                <table className="data-table">
                  <tbody>
                    <tr>
                      <td className="dt-key">Est. Time</td>
                      <td className="dt-val mono">{before.duration_text || '--'}</td>
                    </tr>
                    <tr>
                      <td className="dt-key">Est. Cost</td>
                      <td className="dt-val mono">{formatCurrencyInr(before.estimated_cost_inr)}</td>
                    </tr>
                    <tr>
                      <td className="dt-key">Risk Level</td>
                      <td className="dt-val">
                        <span className={`tag tag--${levelFromRiskLabel(before?.risk?.overall_risk)}`}>
                          {before?.risk?.overall_risk || '--'}
                        </span>
                      </td>
                    </tr>
                    <tr>
                      <td className="dt-key">Reliability</td>
                      <td className="dt-val mono">{formatReliability(before.reliability_score_pct)}</td>
                    </tr>
                  </tbody>
                </table>
              </div>

              <div className="sim-col--divider">
                <span className="sim-arrow">&rarr;</span>
                <span className="sim-disruption-tag">{simResult.requested_disruption_label || disruption}</span>
              </div>

              <div className="sim-col sim-col--after">
                <p className="section-label">After Disruption</p>
                <table className="data-table">
                  <tbody>
                    <tr>
                      <td className="dt-key">Est. Time</td>
                      <td className="dt-val mono">{after.duration_text || '--'}</td>
                    </tr>
                    <tr>
                      <td className="dt-key">Est. Cost</td>
                      <td className="dt-val mono">{formatCurrencyInr(after.estimated_cost_inr)}</td>
                    </tr>
                    <tr>
                      <td className="dt-key">Risk Level</td>
                      <td className="dt-val">
                        <span className={`tag tag--${levelFromRiskLabel(after?.risk?.overall_risk)}`}>
                          {after?.risk?.overall_risk || '--'}
                        </span>
                      </td>
                    </tr>
                    <tr>
                      <td className="dt-key">Reliability</td>
                      <td className="dt-val mono">{formatReliability(after.reliability_score_pct)}</td>
                    </tr>
                  </tbody>
                </table>
              </div>
            </div>

            <hr className="divider" />

            <div className="impact-row">
              <div className="impact-item">
                <span className="impact-label">Delay</span>
                <span className="impact-val impact-val--neg">{formatPercent(simResult.delay_percentage, { signed: true })}</span>
              </div>
              <div className="impact-item">
                <span className="impact-label">Risk Change</span>
                <span className="impact-val impact-val--neutral">{simResult.risk_change || '--'}</span>
              </div>
              <div className="impact-item">
                <span className="impact-label">Cost Increase</span>
                <span className="impact-val impact-val--neg">{formatPercent(simResult.cost_increase_percentage, { signed: true })}</span>
              </div>
            </div>

            <div className="recommendation-box" style={{ marginTop: 12 }}>
              <span className="section-label" style={{ marginBottom: 4 }}>Disruption Advisory</span>
              <p className="recommendation-text">{simResult.summary}</p>
              {simResult.recommendation && (
                <p className="recommendation-text recommendation-text--secondary">{simResult.recommendation}</p>
              )}
            </div>

            <div className="sim-extended-grid">
              <div className="sim-extended-card">
                <p className="section-label">Best Transport Mode Under Scenario</p>
                <div className="sim-best-mode">
                  <span className="sim-best-mode__label">{simResult.best_transport_mode?.label || '--'}</span>
                  <p className="sim-best-mode__text">{simResult.best_transport_mode?.rationale || 'No alternate mode suggestion available.'}</p>
                </div>
              </div>

              <div className="sim-extended-card">
                <p className="section-label">Mitigation Actions</p>
                <ul className="sim-action-list">
                  {(simResult.mitigation_actions || []).map((item, index) => (
                    <li key={`${item}-${index}`}>{item}</li>
                  ))}
                </ul>
              </div>
            </div>
          </div>
        )}
      </div>
    </section>
  )
}
