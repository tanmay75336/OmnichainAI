import { useEffect, useState } from 'react'
import QRCode from 'qrcode'
import SectionCard from './SectionCard'
import MapCanvas from './MapCanvas'
import { toLatLngList } from '../utils/formatters'

function TrackingQr({ value }) {
  const [dataUrl, setDataUrl] = useState('')

  useEffect(() => {
    let active = true

    if (!value) {
      setDataUrl('')
      return undefined
    }

    QRCode.toDataURL(value, {
      width: 180,
      margin: 1,
      color: {
        dark: '#0f1720',
        light: '#ffffff',
      },
    }).then((url) => {
      if (active) {
        setDataUrl(url)
      }
    })

    return () => {
      active = false
    }
  }, [value])

  if (!value || !dataUrl) {
    return <div className="empty-state">QR will generate once a live shipment snapshot is available.</div>
  }

  return <img className="qr-image" src={dataUrl} alt="Shipment tracking QR code" />
}

function buildTrackingQrValue(snapshot) {
  if (!snapshot) {
    return ''
  }

  return JSON.stringify({
    shipmentId: snapshot.shipment_id,
    source: snapshot.source,
    destination: snapshot.destination,
    status: snapshot.current_status,
    progressPct: snapshot.progress_pct,
    trackingMode: snapshot.tracking_mode,
    generatedAt: snapshot.generated_at,
  })
}

export default function TrackingSection({
  trackingDraftId,
  onTrackingDraftIdChange,
  onTrackShipment,
  trackingSnapshot,
  trackingLoading,
  trackingError,
}) {
  const qrValue = buildTrackingQrValue(trackingSnapshot)
  const currentCoordinates = trackingSnapshot?.current_location?.coordinates
  const polyline = toLatLngList(trackingSnapshot?.route_line)
  const destinationPoint = polyline.length ? polyline[polyline.length - 1] : null

  return (
    <div className="tracking-section" id="tracking">
      <div className="tracking-grid">
        <SectionCard
          title="Shipment Tracking"
          subtitle="Shipment ID, current status, real-time backend snapshot"
        >
          <div className="tracking-lookup">
            <div className="tracking-lookup__controls">
              <label className="field">
                <span>Shipment ID</span>
                <input
                  value={trackingDraftId}
                  onChange={(event) => onTrackingDraftIdChange(event.target.value)}
                  placeholder="OMNI-MUM-PUN-20260412-AB12CD"
                />
              </label>
              <button
                type="button"
                className="primary-button"
                onClick={onTrackShipment}
                disabled={!trackingDraftId.trim() || trackingLoading}
              >
                {trackingLoading ? 'Refreshing...' : 'Track Shipment'}
              </button>
            </div>

            {trackingError ? (
              <div className="inline-banner inline-banner--warning">{trackingError}</div>
            ) : null}

            {trackingSnapshot ? (
              <div className="tracking-summary">
                <div className="metric-grid metric-grid--compact">
                  <div className="metric-box">
                    <span>Current status</span>
                    <strong>{trackingSnapshot.current_status}</strong>
                  </div>
                  <div className="metric-box">
                    <span>Progress</span>
                    <strong>{trackingSnapshot.progress_pct}%</strong>
                  </div>
                  <div className="metric-box">
                    <span>Tracking mode</span>
                    <strong>{trackingSnapshot.tracking_mode}</strong>
                  </div>
                </div>

                <div className="tracking-meta">
                  <div>
                    <span>Current location</span>
                    <strong>{trackingSnapshot.current_location?.label}</strong>
                  </div>
                  <div>
                    <span>Storage</span>
                    <strong>{trackingSnapshot.storage_backend}</strong>
                  </div>
                  <div>
                    <span>Snapshot time</span>
                    <strong>{trackingSnapshot.generated_at}</strong>
                  </div>
                </div>

                <p className="report-note">{trackingSnapshot.alternate_route_advice}</p>
              </div>
            ) : (
              <div className="empty-state">
                Tracking activates after route analysis creates a shipment record or when you enter an existing shipment ID.
              </div>
            )}
          </div>
        </SectionCard>

        <SectionCard
          title="Live Map + Tracking"
          subtitle="Current shipment location"
        >
          <MapCanvas
            polyline={polyline}
            markers={[
              polyline[0]
                ? { position: polyline[0], label: trackingSnapshot?.source, kind: 'source' }
                : null,
              destinationPoint
                ? { position: destinationPoint, label: trackingSnapshot?.destination, kind: 'destination' }
                : null,
              currentCoordinates
                ? {
                    position: [currentCoordinates[1], currentCoordinates[0]],
                    label: trackingSnapshot.current_status,
                    kind: 'live',
                  }
                : null,
            ].filter(Boolean)}
            emptyMessage="Run route analysis to create a shipment or load an existing shipment ID."
          />
        </SectionCard>

        <SectionCard
          title="Route Progress Timeline"
          subtitle="Source to destination milestones"
        >
          {trackingSnapshot?.timeline?.length ? (
            <div className="timeline">
              {trackingSnapshot.timeline.map((item) => (
                <article key={item.id} className={`timeline__item timeline__item--${item.status}`}>
                  <div className="timeline__status" />
                  <div>
                    <strong>{item.label}</strong>
                    <p>{item.detail}</p>
                    <small>
                      {item.timestamp} | {item.location}
                    </small>
                  </div>
                </article>
              ))}
            </div>
          ) : (
            <div className="empty-state">
              Timeline data will appear after a shipment snapshot is loaded.
            </div>
          )}
        </SectionCard>

        <SectionCard
          title="QR Code Feature"
          subtitle="Portable shipment lookup"
        >
          <div className="qr-block">
            <TrackingQr value={qrValue} />
            {trackingSnapshot ? (
              <p className="report-note">
                QR payload now comes from the backend tracking snapshot and refreshes when the shipment refreshes.
              </p>
            ) : null}
          </div>
        </SectionCard>
      </div>
    </div>
  )
}
