import React from 'react'
import StatusBadge from './StatusBadge'
import './Header.css'

export default function Header({ backendStatus }) {
  const statusLevel =
    backendStatus === 'online'
      ? 'online'
      : backendStatus === 'offline'
      ? 'offline'
      : 'checking'

  const statusLabel =
    backendStatus === 'online'
      ? 'Backend Online'
      : backendStatus === 'offline'
      ? 'Backend Offline'
      : 'Checking...'

  return (
    <header className="header">
      <div className="header__left">
        <div className="header__logo-mark">SSCOS</div>
        <div className="header__titles">
          <h1 className="header__title">Smart Supply Chain Optimization System</h1>
          <p className="header__subtitle">
            Decision Intelligence for Routing, Risk, and Disruption Planning &mdash; India Operations
          </p>
        </div>
      </div>
      <div className="header__right">
        <div className="header__meta">
          <span className="header__meta-item">v2.4.1</span>
          <span className="header__meta-sep">|</span>
          <span className="header__meta-item">MH-OPS</span>
          <span className="header__meta-sep">|</span>
          <StatusBadge
            level={statusLevel}
            label={statusLabel}
            pulse={backendStatus === 'online'}
          />
        </div>
      </div>
    </header>
  )
}
