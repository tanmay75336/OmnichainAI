import React from 'react'
import './StatusBadge.css'

/**
 * level: 'online' | 'offline' | 'checking' | 'normal' | 'warning' | 'critical' | 'info'
 */
export default function StatusBadge({ level, label, pulse = false }) {
  return (
    <span className={`status-badge status-badge--${level} ${pulse ? 'status-badge--pulse' : ''}`}>
      <span className="status-badge__dot" />
      {label}
    </span>
  )
}
