import React from 'react'
import StatusBadge from './StatusBadge'
import './SupplyChainIntelligence.css'

function toAlertLevel(text, systemStatus) {
  const normalized = String(text || '').toLowerCase()
  if (normalized.includes('high') || normalized.includes('critical') || normalized.includes('shift')) {
    return 'critical'
  }
  if (normalized.includes('monitor') || normalized.includes('risk') || normalized.includes('congestion')) {
    return 'warning'
  }
  return systemStatus === 'critical' ? 'warning' : 'normal'
}

export default function SupplyChainIntelligence({ routeData, simResult }) {
  const intelligence = simResult?.intelligence || routeData?.intelligence
  const decisionSupport = routeData?.decision_support

  return (
    <section className="sci-panel panel">
      <div className="panel__header">
        <span className="panel__header-label">04</span>
        <h2 className="panel__title">Supply Chain Intelligence</h2>
      </div>

      <div className="sci-panel__body">
        {!intelligence ? (
          <div className="sci-placeholder">
            <p className="placeholder-text">Intelligence insights populate after route analysis.</p>
          </div>
        ) : (
          <div className="sci-grid">
            <div className="sci-block">
              <p className="section-label">System Status</p>
              <StatusBadge
                level={intelligence.system_status}
                label={intelligence.system_label}
                pulse={intelligence.system_status === 'critical'}
              />
              <p className="sci-status-sub">
                Predictive corridor monitoring active for weather, infrastructure, and disruption sensitivity.
              </p>
            </div>

            <div className="sci-block sci-block--wide">
              <p className="section-label">Active Alerts</p>
              <ul className="alert-list">
                {intelligence.alerts.map((alert, index) => {
                  const level = toAlertLevel(alert, intelligence.system_status)
                  return (
                    <li key={`${alert}-${index}`} className={`alert-item alert-item--${level}`}>
                      <span className="alert-dot" />
                      <span>{alert}</span>
                    </li>
                  )
                })}
              </ul>
            </div>

            <div className="sci-block">
              <p className="section-label">Fault Detection</p>
              <ul className="fault-list">
                {intelligence.weak_points.map((fault, index) => (
                  <li key={`${fault}-${index}`} className="fault-item">
                    <span className="fault-icon">!</span>
                    <span>{fault}</span>
                  </li>
                ))}
              </ul>
            </div>

            {decisionSupport?.executive_summary && (
              <div className="sci-block sci-block--wide">
                <p className="section-label">Actionable Intelligence</p>
                <div className="sci-summary-box">
                  <p className="sci-summary-text">{decisionSupport.executive_summary}</p>
                  <ul className="sci-action-list">
                    {(decisionSupport.action_items || []).slice(0, 3).map((item, index) => (
                      <li key={`${item}-${index}`}>{item}</li>
                    ))}
                  </ul>
                </div>
              </div>
            )}
          </div>
        )}
      </div>
    </section>
  )
}
