import SectionCard from './SectionCard'

export default function SupplyNewsAlertsPanel({ alerts, newsState, routeData }) {
  return (
    <SectionCard
      title="Supply Chain News + Alerts"
      subtitle="Political issues, holidays, delays, weak points"
    >
      <div className="alerts-layout">
        <div className="report-block">
          <h3>Operational alert board</h3>
          {alerts.length ? (
            <div className="news-stack">
              {alerts.map((alert, index) => (
                <article key={`${alert.title}-${index}`} className={`news-card news-card--${alert.tone || 'normal'}`}>
                  <div className="news-card__header">
                    <strong>{alert.title}</strong>
                    <span>{alert.source}</span>
                  </div>
                  {alert.detail ? <p>{alert.detail}</p> : null}
                </article>
              ))}
            </div>
          ) : (
            <div className="empty-state">
              Alerts will populate after route analysis and simulation.
            </div>
          )}
        </div>

        <div className="report-block">
          <h3>India logistics watch</h3>
          <ul className="bullet-list">
            <li>
              Tier-2 / Tier-3 routing must account for limited last-mile redundancy and longer recovery windows.
            </li>
            <li>
              SEZ movements require stronger compliance timing and congestion-aware gate planning.
            </li>
            <li>
              Monsoon, flood, strike, and holiday disruptions are mapped directly into the simulation engine.
            </li>
            <li>
              {routeData?.india_context?.seasonal_note || 'Seasonal operating note will appear with route intelligence.'}
            </li>
          </ul>

          {newsState.items?.length ? (
            <div className="report-note">
              Gemini is currently supplying route-specific intelligence items for the active corridor.
            </div>
          ) : (
            <div className="report-note">
              External intelligence feed is optional. The system continues to operate on backend route, risk, and simulation data.
            </div>
          )}
        </div>
      </div>
    </SectionCard>
  )
}
