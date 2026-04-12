import SectionCard from './SectionCard'
import StatusPill from './StatusPill'
import { formatNumber } from '../utils/formatters'

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

export default function WeatherNewsPanel({ routeData, weatherTrend, newsState }) {
  const weather = routeData?.weather

  return (
    <SectionCard
      title="Weather + News Panel"
      subtitle="Weather summary, trend signal, external intelligence"
      aside={<NewsStateTag newsState={newsState} />}
    >
      <div className="weather-news-grid">
        <div className="weather-news-block">
          <h3>Weather summary</h3>
          {weather ? (
            <>
              <dl className="report-list report-list--dense">
                <div>
                  <dt>Description</dt>
                  <dd>{weather.description}</dd>
                </div>
                <div>
                  <dt>Rainfall</dt>
                  <dd>{formatNumber(weather.rainfall_mm, 1)} mm</dd>
                </div>
                <div>
                  <dt>Wind speed</dt>
                  <dd>{formatNumber(weather.wind_speed, 1)} m/s</dd>
                </div>
                <div>
                  <dt>Visibility</dt>
                  <dd>{formatNumber(weather.visibility_km, 1)} km</dd>
                </div>
              </dl>

              <div className="trend-strip">
                {weatherTrend.map((point) => (
                  <div key={point.label} className="trend-strip__item">
                    <span>{point.label}</span>
                    <div className="trend-strip__bar">
                      <div
                        className="trend-strip__fill"
                        style={{ height: `${point.level}%` }}
                      />
                    </div>
                    <strong>{point.level}</strong>
                  </div>
                ))}
              </div>
            </>
          ) : (
            <div className="empty-state">
              Weather and trend data will appear after route analysis.
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
