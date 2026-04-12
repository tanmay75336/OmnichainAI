import SectionCard from './SectionCard'

export default function RecommendationPanel({ routeData, simulationResult }) {
  const decisionSupport = routeData?.decision_support
  const recommendation = routeData?.suggested_transport_mode

  return (
    <SectionCard
      title="Recommendation Engine"
      subtitle="Transport switch, mitigation, route stages"
    >
      {routeData ? (
        <div className="recommendation-grid">
          <div className="recommendation-callout">
            <span>Primary recommendation</span>
            <strong>{recommendation?.rationale}</strong>
            <p>{decisionSupport?.executive_summary}</p>
          </div>

          <div className="report-block">
            <h3>Mitigation strategy</h3>
            <ul className="bullet-list">
              {decisionSupport?.action_items?.map((item) => (
                <li key={item}>{item}</li>
              ))}
              {simulationResult?.mitigation_actions?.map((item) => (
                <li key={item}>{item}</li>
              ))}
            </ul>
          </div>

          <div className="report-block">
            <h3>Distribution model</h3>
            <p className="report-copy">
              {decisionSupport?.distribution_model?.model}
            </p>
            <p className="report-copy">
              {decisionSupport?.distribution_model?.description}
            </p>
            <p className="report-note">{decisionSupport?.last_mile_strategy}</p>
          </div>

          <div className="report-block">
            <h3>Route stages</h3>
            <ul className="bullet-list">
              {decisionSupport?.route_stages?.map((stage) => (
                <li key={stage.stage}>
                  <strong>{stage.stage}:</strong> {stage.detail}
                </li>
              ))}
            </ul>
          </div>
        </div>
      ) : (
        <div className="empty-state">
          The recommendation engine will populate after the first route analysis.
        </div>
      )}
    </SectionCard>
  )
}
