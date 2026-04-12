import { useEffect, useState } from 'react'
import QRCode from 'qrcode'
import SectionCard from './SectionCard'
import MapCanvas from './MapCanvas'
import { buildTrackingQrValue } from '../utils/tracking'

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
    return <div className="empty-state">QR will generate once a shipment record is available.</div>
  }

  return <img className="qr-image" src={dataUrl} alt="Shipment tracking QR code" />
}

export default function TrackingSection({
  shipmentLookupId,
  onShipmentLookupIdChange,
  shipmentRecord,
  shipmentFound,
}) {
  const qrValue = buildTrackingQrValue(shipmentFound)

  return (
    <div className="tracking-section" id="tracking">
      <div className="tracking-grid">
        <SectionCard
          title="Shipment Tracking"
          subtitle="Shipment ID, current status, alternate action"
        >
          <div className="tracking-lookup">
            <label className="field">
              <span>Shipment ID</span>
              <input
                value={shipmentLookupId}
                onChange={(event) => onShipmentLookupIdChange(event.target.value)}
                placeholder="OMNI-MUM-PUN-20260412"
              />
            </label>

            {shipmentFound ? (
              <div className="tracking-summary">
                <div className="metric-grid metric-grid--compact">
                  <div className="metric-box">
                    <span>Current status</span>
                    <strong>{shipmentFound.currentStatus}</strong>
                  </div>
                  <div className="metric-box">
                    <span>Progress</span>
                    <strong>{shipmentFound.progressLabel}</strong>
                  </div>
                </div>
                <p className="report-copy">
                  Live location: {shipmentFound.currentLocation.label}
                </p>
                <p className="report-note">{shipmentFound.alternateAction}</p>
              </div>
            ) : shipmentRecord ? (
              <div className="inline-banner inline-banner--warning">
                Shipment ID not found. Use {shipmentRecord.shipmentId} to inspect the generated tracking record for the active corridor.
              </div>
            ) : (
              <div className="empty-state">
                Tracking activates after a route analysis generates a shipment record.
              </div>
            )}
          </div>
        </SectionCard>

        <SectionCard
          title="Live Map + Tracking"
          subtitle="Current shipment location"
        >
          <MapCanvas
            polyline={shipmentFound?.routeLine || []}
            markers={[
              shipmentFound?.routeLine?.[0]
                ? { position: shipmentFound.routeLine[0], label: shipmentFound.source, kind: 'source' }
                : null,
              shipmentFound?.routeLine?.[1]
                ? { position: shipmentFound.routeLine[1], label: shipmentFound.destination, kind: 'destination' }
                : null,
              shipmentFound?.currentLocation?.coordinates
                ? {
                    position: [
                      shipmentFound.currentLocation.coordinates[1],
                      shipmentFound.currentLocation.coordinates[0],
                    ],
                    label: shipmentFound.currentStatus,
                    kind: 'live',
                  }
                : null,
            ].filter(Boolean)}
            emptyMessage="Run route analysis, then use the generated shipment ID to open the live tracking view."
          />
        </SectionCard>

        <SectionCard
          title="Route Progress Timeline"
          subtitle="Source to destination milestones"
        >
          {shipmentFound?.timeline?.length ? (
            <div className="timeline">
              {shipmentFound.timeline.map((item) => (
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
              Timeline data will appear after tracking is initialized from a route analysis.
            </div>
          )}
        </SectionCard>

        <SectionCard
          title="QR Code Feature"
          subtitle="Portable shipment lookup"
        >
          <div className="qr-block">
            <TrackingQr value={qrValue} />
            {shipmentFound ? (
              <p className="report-note">
                QR payload contains shipment ID, source, destination, status, and progress for quick lookup.
              </p>
            ) : null}
          </div>
        </SectionCard>
      </div>
    </div>
  )
}
