import SectionCard from './SectionCard'
import StatusPill from './StatusPill'
import { formatDateLabel, formatNumber } from '../utils/formatters'

function NewsStateTag({ newsState }) {
  if (newsState.status === 'ready') {
    return <StatusPill label="Gemini active" tone="success" />
  }
  if (newsState.status === 'loading') {
    return <StatusPill label="Loading feed" tone="warning" />
  }
  if (newsState.status === 'error') {
    return <StatusPill label="Feed error" tone="danger" />
  }
  if (newsState.status === 'not_configured') {
    return <StatusPill label="Gemini key missing" tone="warning" />
  }
  return <StatusPill label="Awaiting route" tone="neutral" />
}

export default function WeatherNewsPanel({ routeData, newsState }) {
  const weather = routeData?.weather
  const weatherOutlook = routeData?.weather_outlook || []

  return (
    <SectionCard
      title="Weather + News Panel"
      subtitle="Current conditions and the upcoming route weather outlook"
      aside={<NewsStateTag newsState={newsState} />}
    >
      <div className="weather-news-grid">
        <div className="weather-news-block">
          <h3>Route weather overview</h3>
          {weather ? (
            <>
              <dl className="report-list report-list--dense">
                <div>
                  <dt>Current description</dt>
                  <dd>{weather.description}</dd>
                </div>
                <div>
                  <dt>Temperature</dt>
                  <dd>{formatNumber(weather.temperature, 1)} C</dd>
                </div>
                <div>
                  <dt>Rainfall</dt>
                  <dd>{formatNumber(weather.rainfall_mm, 1)} mm</dd>
                </div>
                <div>
                  <dt>Visibility</dt>
                  <dd>{formatNumber(weather.visibility_km, 1)} km</dd>
                </div>
              </dl>

              <div className="table-wrap">
                <table className="intelligence-table">
                  <thead>
                    <tr>
                      <th>Date</th>
                      <th>Avg Temp</th>
                      <th>Range</th>
                      <th>Condition</th>
                    </tr>
                  </thead>
                  <tbody>
                    {weatherOutlook.map((day) => (
                      <tr key={`${day.date || day.date_index}`}>
                        <td>{day.date ? formatDateLabel(day.date) : `Day ${day.date_index + 1}`}</td>
                        <td>{formatNumber(day.avg_temp_c, 1)} C</td>
                        <td>
                          {formatNumber(day.min_temp_c, 1)} C
                          {' / '}
                          {formatNumber(day.max_temp_c, 1)} C
                        </td>
                        <td>{day.condition_label}</td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            </>
          ) : (
            <div className="empty-state">
              Weather and weekly route outlook will appear after route analysis.
            </div>
          )}
        </div>

        <div className="weather-news-block">
          <h3>Supply chain / weather / political news</h3>
          {newsState.summary ? <p className="report-copy">{newsState.summary}</p> : null}
          {newsState.items?.length ? (
            <div className="news-stack">
              {newsState.items.map((item, index) => (
                <article key={`${item.headline}-${index}`} className="news-card">
                  <div className="news-card__header">
                    <strong>{item.headline}</strong>
                    <span>{item.tag}</span>
                  </div>
                  <p>{item.detail}</p>
                  <small>{item.recommended_action}</small>
                </article>
              ))}
            </div>
          ) : (
            <div className="empty-state">
              {newsState.status === 'not_configured'
                ? 'Add the Gemini API key to enable AI-generated route intelligence news.'
                : 'The news feed will populate after route analysis.'}
            </div>
          )}
        </div>
      </div>
    </SectionCard>
  )
}
