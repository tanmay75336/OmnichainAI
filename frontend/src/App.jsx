import React, { useEffect, useState } from 'react'
import Header from './components/Header'
import RouteForm from './components/RouteForm'
import RouteResults from './components/RouteResults'
import SimulationPanel from './components/SimulationPanel'
import SupplyChainIntelligence from './components/SupplyChainIntelligence'
import IndiaContextPanel from './components/IndiaContextPanel'
import { checkHealth, getRoute, runSimulation } from './services/api'
import './styles/App.css'

export default function App() {
  const [backendStatus, setBackendStatus] = useState('checking')
  const [routeLoading, setRouteLoading] = useState(false)
  const [routeData, setRouteData] = useState(null)
  const [routeError, setRouteError] = useState('')
  const [activeRegion, setActiveRegion] = useState('tier_2')

  const [simLoading, setSimLoading] = useState(false)
  const [simResult, setSimResult] = useState(null)
  const [simError, setSimError] = useState('')

  useEffect(() => {
    const ping = async () => {
      try {
        await checkHealth()
        setBackendStatus('online')
      } catch {
        setBackendStatus('offline')
      }
    }

    ping()
    const interval = setInterval(ping, 30000)
    return () => clearInterval(interval)
  }, [])

  const handleRouteSubmit = async (params) => {
    setRouteLoading(true)
    setRouteError('')
    setSimResult(null)
    setSimError('')
    setActiveRegion(params.region_type)

    try {
      const data = await getRoute(params)
      setRouteData(data)
      setActiveRegion(data?.region_type || params.region_type)
    } catch (err) {
      setRouteData(null)
      setRouteError(err.message || 'Failed to fetch route data.')
    } finally {
      setRouteLoading(false)
    }
  }

  const handleSimulate = async ({ route, disruptionLabel }) => {
    setSimLoading(true)
    setSimError('')
    setSimResult(null)

    try {
      const data = await runSimulation({ route, disruptionLabel })
      setSimResult(data)
    } catch (err) {
      setSimError(err.message || 'Simulation failed.')
    } finally {
      setSimLoading(false)
    }
  }

  return (
    <div className="app">
      <Header backendStatus={backendStatus} />

      <main className="app__main">
        <div className="app__col app__col--left">
          <RouteForm
            onSubmit={handleRouteSubmit}
            loading={routeLoading}
          />
          <RouteResults
            data={routeData}
            loading={routeLoading}
            error={routeError}
          />
          <SimulationPanel
            routeData={routeData}
            onSimulate={handleSimulate}
            simResult={simResult}
            simLoading={simLoading}
            simError={simError}
          />
        </div>

        <div className="app__col app__col--right">
          <SupplyChainIntelligence
            routeData={routeData}
            simResult={simResult}
          />
          <IndiaContextPanel
            activeRegion={activeRegion}
            routeData={routeData}
          />
        </div>
      </main>

      <footer className="app__footer">
        <span className="mono">SSCOS v2.4.1</span>
        <span className="footer-sep">·</span>
        <span>India Operations Division</span>
        <span className="footer-sep">·</span>
        <span>Routing Intelligence Module</span>
        <span className="footer-sep">·</span>
        <span className="mono" style={{ color: 'var(--text-muted)' }}>
          {new Date().toLocaleDateString('en-IN', {
            day: '2-digit',
            month: 'short',
            year: 'numeric',
          })}
        </span>
      </footer>
    </div>
  )
}
