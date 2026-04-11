import React from 'react'
import './IndiaContextPanel.css'

const DEFAULT_REGION_CARDS = [
  {
    code: 'tier_2',
    label: 'TIER-2',
    connectivity_label: 'Moderate',
    infrastructure_quality: 'National-highway connectivity with partial expressway access.',
    last_mile_profile: 'Decent last-mile performance with moderate suburban delivery variability.',
    sez_exit_delay_risk: 'Medium',
    recommended_buffer_hours: 6,
    description: 'Tier-2 region with moderate infrastructure resiliency and mid-mile uncertainty.',
  },
  {
    code: 'tier_3',
    label: 'TIER-3',
    connectivity_label: 'Weak',
    infrastructure_quality: 'State-highway and district-road dependency with limited redundancy.',
    last_mile_profile: 'High last-mile delay probability and lower warehousing depth.',
    sez_exit_delay_risk: 'High',
    recommended_buffer_hours: 12,
    description: 'Tier-3 region with higher last-mile vulnerability and lower infrastructure redundancy.',
  },
  {
    code: 'sez',
    label: 'SEZ',
    connectivity_label: 'Strong',
    infrastructure_quality: 'Dedicated industrial infrastructure with better customs/process readiness.',
    last_mile_profile: 'Stable internal last-mile movement with controlled gate operations.',
    sez_exit_delay_risk: 'Medium',
    recommended_buffer_hours: 4,
    description: 'SEZ corridor with stronger infrastructure, customs readiness, and lower disruption exposure.',
  },
]

const SEASONAL_RISKS = [
  { period: 'Jun-Sep', label: 'Monsoon Season', impact: 'High', desc: 'Road disruptions, flooding in low-lying corridors, and port congestion.' },
  { period: 'Oct-Nov', label: 'Festival Window', impact: 'Medium', desc: 'Labor variability, holiday closures, and demand surges across key hubs.' },
  { period: 'Dec-Feb', label: 'Winter Fog', impact: 'Medium', desc: 'Visibility issues for North India road and air corridors.' },
  { period: 'Mar-May', label: 'Pre-Monsoon', impact: 'Low', desc: 'Preferred planning window for bulk movements and inventory repositioning.' },
]

const impactTag = (level) => {
  if (level === 'High') return 'tag tag--critical'
  if (level === 'Medium') return 'tag tag--warning'
  return 'tag tag--normal'
}

export default function IndiaContextPanel({ activeRegion, routeData }) {
  const indiaContext = routeData?.india_context
  const cards = indiaContext?.region_cards || DEFAULT_REGION_CARDS

  return (
    <section className="india-panel panel">
      <div className="panel__header">
        <span className="panel__header-label">05</span>
        <h2 className="panel__title">India Logistics Context</h2>
        <span className="panel__header-sub">Reference Intelligence - Regional Infrastructure & Seasonal Risk</span>
      </div>

      <div className="india-panel__body">
        <div className="india-tier-grid">
          {cards.map((card) => (
            <div
              key={card.code}
              className={`tier-card ${activeRegion === card.code ? 'tier-card--active' : ''}`}
            >
              <div className="tier-card__header">
                <span className="tier-card__label">{card.label}</span>
                <span className={impactTag(card.code === 'tier_3' ? 'High' : card.code === 'tier_2' ? 'Medium' : 'Low')}>
                  {card.connectivity_label}
                </span>
              </div>

              <table className="data-table tier-card__table">
                <tbody>
                  <tr>
                    <td className="dt-key">Infrastructure</td>
                    <td className="dt-val tier-card__text">{card.infrastructure_quality}</td>
                  </tr>
                  <tr>
                    <td className="dt-key">Last Mile</td>
                    <td className="dt-val tier-card__text">{card.last_mile_profile}</td>
                  </tr>
                  <tr>
                    <td className="dt-key">SEZ Exit Delay</td>
                    <td className="dt-val">
                      <span className={impactTag(card.sez_exit_delay_risk === 'High' ? 'High' : card.sez_exit_delay_risk === 'Medium' ? 'Medium' : 'Low')}>
                        {card.sez_exit_delay_risk}
                      </span>
                    </td>
                  </tr>
                  <tr>
                    <td className="dt-key">Buffer Advice</td>
                    <td className="dt-val mono">{card.recommended_buffer_hours} hrs</td>
                  </tr>
                </tbody>
              </table>
              <p className="tier-card__note">{card.description}</p>
            </div>
          ))}
        </div>

        {indiaContext?.seasonal_note && (
          <>
            <hr className="divider" />
            <div className="india-note">{indiaContext.seasonal_note}</div>
          </>
        )}

        <hr className="divider" />

        <p className="section-label">Seasonal Risk Calendar</p>
        <div className="seasonal-grid">
          {SEASONAL_RISKS.map((season) => (
            <div key={season.period} className="seasonal-item">
              <div className="seasonal-header">
                <span className="seasonal-period mono">{season.period}</span>
                <span className={impactTag(season.impact)}>{season.impact}</span>
              </div>
              <p className="seasonal-name">{season.label}</p>
              <p className="seasonal-desc">{season.desc}</p>
            </div>
          ))}
        </div>
      </div>
    </section>
  )
}
