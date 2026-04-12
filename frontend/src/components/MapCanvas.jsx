import { useEffect, useRef } from 'react'
import L from 'leaflet'

export default function MapCanvas({
  center = [22.9734, 78.6569],
  zoom = 5,
  polyline = [],
  markers = [],
  emptyMessage = 'Map will appear after route data is available.',
}) {
  const containerRef = useRef(null)
  const mapRef = useRef(null)
  const layerGroupRef = useRef(null)

  useEffect(() => {
    if (!containerRef.current || mapRef.current) {
      return undefined
    }

    mapRef.current = L.map(containerRef.current, {
      zoomControl: false,
      scrollWheelZoom: false,
    }).setView(center, zoom)

    L.tileLayer('https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png', {
      attribution: '&copy; OpenStreetMap contributors',
    }).addTo(mapRef.current)

    L.control.zoom({ position: 'bottomright' }).addTo(mapRef.current)
    layerGroupRef.current = L.layerGroup().addTo(mapRef.current)

    return () => {
      mapRef.current?.remove()
      mapRef.current = null
    }
  }, [center, zoom])

  useEffect(() => {
    if (!mapRef.current || !layerGroupRef.current) {
      return
    }

    layerGroupRef.current.clearLayers()
    const bounds = []

    if (polyline.length >= 2) {
      const line = L.polyline(polyline, {
        color: '#1f5f8b',
        weight: 4,
        opacity: 0.85,
        dashArray: '10 6',
      }).addTo(layerGroupRef.current)
      bounds.push(...line.getLatLngs())
    }

    markers.forEach((marker) => {
      if (!marker.position) {
        return
      }

      const circle = L.circleMarker(marker.position, {
        radius: marker.kind === 'live' ? 8 : 6,
        color:
          marker.kind === 'destination'
            ? '#b25a2b'
            : marker.kind === 'live'
              ? '#0f766e'
              : '#102a43',
        fillColor:
          marker.kind === 'destination'
            ? '#f8d3bd'
            : marker.kind === 'live'
              ? '#9fe8db'
              : '#dbe9f6',
        fillOpacity: 1,
        weight: 2,
      }).addTo(layerGroupRef.current)

      if (marker.label) {
        circle.bindTooltip(marker.label, {
          direction: 'top',
          offset: [0, -6],
        })
      }

      bounds.push(circle.getLatLng())
    })

    if (bounds.length) {
      mapRef.current.fitBounds(bounds, { padding: [32, 32] })
    } else {
      mapRef.current.setView(center, zoom)
    }
  }, [center, zoom, markers, polyline])

  const isEmpty = !polyline.length && !markers.length

  return (
    <div className="map-shell">
      <div ref={containerRef} className="map-canvas" />
      {isEmpty ? <div className="map-shell__empty">{emptyMessage}</div> : null}
    </div>
  )
}
