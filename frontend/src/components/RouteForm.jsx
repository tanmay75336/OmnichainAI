import React, { useState } from 'react'
import './RouteForm.css'

const TRANSPORT_MODES = [
  { value: 'road', label: 'Road' },
  { value: 'rail', label: 'Rail' },
  { value: 'air', label: 'Air' },
  { value: 'waterways', label: 'Waterways' },
]

const REGION_TYPES = [
  { value: 'tier_2', label: 'Tier-2 City' },
  { value: 'tier_3', label: 'Tier-3 City' },
  { value: 'sez', label: 'SEZ Zone' },
]

const MAJOR_CITIES = [
  'Mumbai', 'Pune', 'Delhi', 'Bangalore', 'Chennai', 'Hyderabad',
  'Ahmedabad', 'Kolkata', 'Surat', 'Jaipur', 'Lucknow', 'Nagpur',
  'Indore', 'Bhopal', 'Coimbatore', 'Visakhapatnam', 'Kochi', 'Nashik',
]

export default function RouteForm({ onSubmit, loading }) {
  const [source, setSource] = useState('Mumbai')
  const [destination, setDestination] = useState('Chennai')
  const [transportMode, setTransportMode] = useState('road')
  const [regionType, setRegionType] = useState('tier_3')
  const [error, setError] = useState('')

  const handleSubmit = () => {
    setError('')
    if (!source.trim()) return setError('Source city is required.')
    if (!destination.trim()) return setError('Destination city is required.')
    if (source.trim().toLowerCase() === destination.trim().toLowerCase()) {
      return setError('Source and destination cannot be the same.')
    }

    onSubmit({
      source: source.trim(),
      destination: destination.trim(),
      transport_mode: transportMode,
      region_type: regionType,
    })
  }

  return (
    <section className="route-form panel">
      <div className="panel__header">
        <span className="panel__header-label">01</span>
        <h2 className="panel__title">Route Analysis Input</h2>
      </div>

      <div className="route-form__body">
        <div className="form-row">
          <div className="form-group">
            <label className="form-label">Source City</label>
            <input
              className="form-input"
              type="text"
              list="city-list"
              placeholder="e.g. Mumbai"
              value={source}
              onChange={(e) => setSource(e.target.value)}
              disabled={loading}
            />
          </div>
          <div className="form-group form-group--arrow">
            <span className="route-arrow">&rarr;</span>
          </div>
          <div className="form-group">
            <label className="form-label">Destination City</label>
            <input
              className="form-input"
              type="text"
              list="city-list"
              placeholder="e.g. Chennai"
              value={destination}
              onChange={(e) => setDestination(e.target.value)}
              disabled={loading}
            />
          </div>
        </div>

        <datalist id="city-list">
          {MAJOR_CITIES.map((city) => (
            <option key={city} value={city} />
          ))}
        </datalist>

        <div className="form-row form-row--secondary">
          <div className="form-group">
            <label className="form-label">Transport Mode</label>
            <select
              className="form-select"
              value={transportMode}
              onChange={(e) => setTransportMode(e.target.value)}
              disabled={loading}
            >
              {TRANSPORT_MODES.map((mode) => (
                <option key={mode.value} value={mode.value}>{mode.label}</option>
              ))}
            </select>
          </div>
          <div className="form-group">
            <label className="form-label">Region Classification</label>
            <select
              className="form-select"
              value={regionType}
              onChange={(e) => setRegionType(e.target.value)}
              disabled={loading}
            >
              {REGION_TYPES.map((region) => (
                <option key={region.value} value={region.value}>{region.label}</option>
              ))}
            </select>
          </div>
          <div className="form-group form-group--action">
            <label className="form-label">&nbsp;</label>
            <button
              className="btn-primary"
              onClick={handleSubmit}
              disabled={loading}
            >
              {loading ? 'Analyzing...' : 'Run Route Analysis'}
            </button>
          </div>
        </div>

        {error && <div className="error-inline">{error}</div>}
      </div>
    </section>
  )
}
