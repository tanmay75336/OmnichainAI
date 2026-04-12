import SectionCard from './SectionCard'
import { formatCurrency, formatPercent } from '../utils/formatters'

export default function ModalComparisonPanel({ routeData }) {
  const options = routeData?.modal_options || []

  return (
    <SectionCard
      title="Multi-Modal Comparison"
      subtitle="Road / Rail / Air / Waterways"
      aside={<span className="section-card__hint">Table-first comparison, as requested</span>}
    >
      {options.length ? (
        <div className="table-wrap">
          <table className="intelligence-table">
            <thead>
              <tr>
                <th>Mode</th>
                <th>Time</th>
                <th>Cost</th>
                <th>Risk</th>
                <th>Reliability</th>
                <th>Action</th>
              </tr>
            </thead>
            <tbody>
              {options.map((option) => (
                <tr
                  key={option.mode}
                  className={option.is_recommended ? 'intelligence-table__row--recommended' : ''}
                >
                  <td>{option.label}</td>
                  <td>{option.duration_text}</td>
                  <td>{formatCurrency(option.estimated_cost_inr)}</td>
                  <td>{option.overall_risk}</td>
                  <td>{formatPercent(option.reliability_score_pct)}</td>
                  <td>{option.is_recommended ? 'Preferred under current risk' : 'Standby option'}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      ) : (
        <div className="empty-state">
          The transport comparison matrix will populate after route analysis.
        </div>
      )}
    </SectionCard>
  )
}
