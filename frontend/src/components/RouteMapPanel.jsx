import SectionCard from './SectionCard'
import MapCanvas from './MapCanvas'
import { formatCurrency, formatNumber, toLatLng, toLatLngList } from '../utils/formatters'

export default function RouteMapPanel({ routeData }) {
  const route = routeData?.route
  const sourcePosition = toLatLng(route?.source_coordinates)
  const destinationPosition = toLatLng(route?.destination_coordinates)
  const primaryLine = toLatLngList(route?.geometry_coordinates)
  const traffic = route?.traffic_analysis
  const alternativeLines = (traffic?.alternative_routes || [])
    .filter((item) => item.geometry_coordinates?.length >= 2)
    .slice(0, 2)
    .map((item) => ({
      positions: toLatLngList(item.geometry_coordinates),
      color: item.is_recommended ? '#b25a2b' : '#5b7c99',
      weight: item.is_recommended ? 5 : 3,
      opacity: item.is_recommended ? 0.92 : 0.65,
      dashArray: item.is_recommended ? '10 8' : '6 8',
      label: item.label,
    }))

  const directionSteps = route?.directions_preview || []
  const polylines = [
    ...alternativeLines,
    primaryLine.length >= 2
      ? {
          positions: primaryLine,
          color: '#1f5f8b',
          weight: 5,
          opacity: 0.92,
          label: 'Primary route',
        }
      : null,
  ].filter(Boolean)

  return (
    <SectionCard
      title="Route Map View"
      subtitle="Address geocoding, route line, alternate corridor, and turn preview"
      aside={<span className="section-card__hint">Leaflet / OpenStreetMap</span>}
    >
      <div className="map-panel">
        <MapCanvas
          polylines={polylines}
          markers={[
            sourcePosition ? { position: sourcePosition, label: route.source_details?.label || route.source, kind: 'source' } : null,
            destinationPosition ? { position: destinationPosition, label: route.destination_details?.label || route.destination, kind: 'destination' } : null,
          ].filter(Boolean)}
          emptyMessage="Analyze a route to render the corridor map."
        />

        {route ? (
          <>
            <div className="report-note">
              {route.source}
              {' -> '}
              {route.destination}
              {' | '}
              {route.distance_text}
              {' | '}
              {route.duration_text}
            </div>

            {traffic ? (
              <div className="report-grid">
                <div className="report-block">
                  <h3>Traffic-aware alternate route</h3>
                  <p className="report-copy">{traffic.advisory}</p>
                  <dl className="report-list report-list--dense">
                    <div>
                      <dt>Projected delay</dt>
                      <dd>{traffic.projected_delay_minutes} mins</dd>
                    </div>
                    <div>
                      <dt>Projected primary ETA</dt>
                      <dd>{traffic.projected_primary_duration_minutes} mins</dd>
                    </div>
                    <div>
                      <dt>Traffic model</dt>
                      <dd>{traffic.is_live_traffic ? 'Live feed' : 'Operational estimate'}</dd>
                    </div>
                  </dl>
                </div>

                <div className="report-block">
                  <h3>Recommended alternate</h3>
                  {traffic.recommended_alternate ? (
                    <dl className="report-list report-list--dense">
                      <div>
                        <dt>Route</dt>
                        <dd>{traffic.recommended_alternate.label}</dd>
                      </div>
                      <div>
                        <dt>Time saved</dt>
                        <dd>{traffic.recommended_alternate.time_saved_minutes} mins</dd>
                      </div>
                      <div>
                        <dt>Extra distance</dt>
                        <dd>{formatNumber(traffic.recommended_alternate.extra_distance_km, 1)} km</dd>
                      </div>
                      <div>
                        <dt>Fuel change</dt>
                        <dd>{formatCurrency(traffic.recommended_alternate.fuel_delta_inr)}</dd>
                      </div>
                    </dl>
                  ) : (
                    <div className="empty-state">
                      No faster alternate road corridor is currently projected for this route.
                    </div>
                  )}
                </div>
              </div>
            ) : null}

            <div className="report-block">
              <h3>Turn-by-turn preview</h3>
              {directionSteps.length ? (
                <ul className="bullet-list">
                  {directionSteps.map((step, index) => (
                    <li key={`${step.instruction}-${index}`}>
                      <strong>{step.instruction}</strong>
                      {' '}
                      ({step.distance_text} / {step.duration_text})
                    </li>
                  ))}
                </ul>
              ) : (
                <div className="empty-state">
                  Step directions will appear when the routing provider returns instruction data.
                </div>
              )}
            </div>
          </>
        ) : null}
      </div>
    </SectionCard>
  )
}
