import SectionCard from './SectionCard'
import MapCanvas from './MapCanvas'
import { toLatLng } from '../utils/formatters'

export default function RouteMapPanel({ routeData }) {
  const route = routeData?.route
  const sourcePosition = toLatLng(route?.source_coordinates)
  const destinationPosition = toLatLng(route?.destination_coordinates)
  const line = sourcePosition && destinationPosition ? [sourcePosition, destinationPosition] : []

  return (
    <SectionCard
      title="Route Map View"
      subtitle="Source to destination map"
      aside={<span className="section-card__hint">Leaflet / OpenStreetMap</span>}
    >
      <div className="map-panel">
        <MapCanvas
          polyline={line}
          markers={[
            sourcePosition ? { position: sourcePosition, label: route.source, kind: 'source' } : null,
            destinationPosition ? { position: destinationPosition, label: route.destination, kind: 'destination' } : null,
          ].filter(Boolean)}
          emptyMessage="Analyze a route to render the corridor map."
        />

        {route ? (
          <div className="report-note">
            {route.source}
            {' -> '}
            {route.destination}
            {' | '}
            {route.distance_text}
            {' | '}
            {route.duration_text}
          </div>
        ) : null}
      </div>
    </SectionCard>
  )
}
