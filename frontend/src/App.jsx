import React, { useEffect, useMemo, useState } from 'react'
import TopBar from './components/TopBar'
import RouteAnalysisPanel from './components/RouteAnalysisPanel'
import ModalComparisonPanel from './components/ModalComparisonPanel'
import WeatherDisruptionPanel from './components/WeatherDisruptionPanel'
import WeatherNewsPanel from './components/WeatherNewsPanel'
import RecommendationPanel from './components/RecommendationPanel'
import RouteMapPanel from './components/RouteMapPanel'
import SupplyNewsAlertsPanel from './components/SupplyNewsAlertsPanel'
import TrackingSection from './components/TrackingSection'
import {
  checkHealth,
  createTrackingShipment,
  getRoute,
  getTrackingShipment,
  simulateRoute,
} from './services/api'
import {
  fetchGeminiOperationalNews,
  getGeminiConfigState,
} from './services/gemini'
import {
  buildOperationalAlerts,
  deriveDisruptionSignals,
  getTodayDateString,
} from './utils/intelligence'

const DEFAULT_FORM = {
  source: 'Warehouse 14, Wagle Industrial Estate, Thane, Maharashtra 400604',
  destination: 'Shop No. 100, Hiranandani Estate, Thane West, Mumbai, Maharashtra 400607',
  transport_mode: 'road',
  cargo: {
    weight_kg: '120',
    quantity: '24',
    dimensions_cm: {
      length: '60',
      width: '45',
      height: '35',
    },
  },
}

const DEFAULT_NEWS_STATE = {
  status: 'idle',
  summary: '',
  items: [],
}

export default function App() {
  const [backendHealth, setBackendHealth] = useState(null)
  const [backendStatus, setBackendStatus] = useState('checking')
  const [routeForm, setRouteForm] = useState(DEFAULT_FORM)
  const [shipmentDate, setShipmentDate] = useState(getTodayDateString())

  const [routeData, setRouteData] = useState(null)
  const [routeLoading, setRouteLoading] = useState(false)
  const [routeError, setRouteError] = useState('')

  const [selectedDisruptionId, setSelectedDisruptionId] = useState('monsoon')
  const [simulationLoading, setSimulationLoading] = useState(false)
  const [simulationResult, setSimulationResult] = useState(null)
  const [simulationError, setSimulationError] = useState('')

  const [newsState, setNewsState] = useState(DEFAULT_NEWS_STATE)
  const [trackingDraftId, setTrackingDraftId] = useState('')
  const [activeTrackingId, setActiveTrackingId] = useState('')
  const [trackingSnapshot, setTrackingSnapshot] = useState(null)
  const [trackingLoading, setTrackingLoading] = useState(false)
  const [trackingError, setTrackingError] = useState('')

  useEffect(() => {
    async function pingBackend() {
      try {
        const data = await checkHealth()
        setBackendHealth(data)
        setBackendStatus('online')
      } catch {
        setBackendStatus('offline')
      }
    }

    pingBackend()
    const interval = window.setInterval(pingBackend, 30000)
    return () => window.clearInterval(interval)
  }, [])

  const disruptionSignals = useMemo(
    () => deriveDisruptionSignals({ routeData, shipmentDate }),
    [routeData, shipmentDate]
  )

  const alerts = useMemo(
    () =>
      buildOperationalAlerts({
        routeData,
        shipmentDate,
        simulationResult,
        newsState,
      }),
    [routeData, shipmentDate, simulationResult, newsState]
  )

  const serviceStatus = useMemo(
    () => ({
      backend: backendStatus,
      routing: routeData ? (routeData.route?.is_fallback ? 'fallback' : 'live') : 'checking',
      weather: routeData ? (routeData.weather?.is_fallback ? 'fallback' : 'live') : 'checking',
      gemini:
        newsState.status === 'ready' || backendHealth?.gemini?.configured
          ? 'live'
          : newsState.status === 'error'
            ? 'error'
            : newsState.status === 'not_configured'
              ? backendHealth?.gemini?.configured
                ? 'configured'
                : 'missing'
              : getGeminiConfigState(),
    }),
    [backendHealth?.gemini?.configured, backendStatus, newsState, routeData]
  )

  async function handleAnalyzeRoute() {
    setRouteLoading(true)
    setRouteError('')
    setSimulationResult(null)
    setSimulationError('')
    setTrackingError('')

    try {
      const data = await getRoute(routeForm)
      setRouteData(data)
      try {
        const tracking = await createTrackingShipment({
          source: routeForm.source,
          destination: routeForm.destination,
          transport_mode: routeForm.transport_mode,
          region_type: data.region_type,
          cargo: routeForm.cargo,
          shipment_date: shipmentDate,
        })
        setTrackingSnapshot(tracking)
        setTrackingDraftId(tracking.shipment_id)
        setActiveTrackingId(tracking.shipment_id)
      } catch (trackingInitError) {
        setTrackingSnapshot(null)
        setTrackingError(trackingInitError.message || 'Tracking initialization failed.')
      }
    } catch (error) {
      setRouteData(null)
      setTrackingSnapshot(null)
      setRouteError(error.message || 'Failed to analyze route.')
    } finally {
      setRouteLoading(false)
    }
  }

  async function handleSimulateDisruption() {
    if (!routeData?.route) {
      return
    }

    setSimulationLoading(true)
    setSimulationError('')

    try {
      const data = await simulateRoute({
        route: routeData.route,
        disruptionId: selectedDisruptionId,
      })
      setSimulationResult(data)
    } catch (error) {
      setSimulationError(error.message || 'Simulation failed.')
    } finally {
      setSimulationLoading(false)
    }
  }

  function handleTrackShipment() {
    const nextId = trackingDraftId.trim().toUpperCase()
    if (!nextId) {
      return
    }
    setTrackingError('')
    if (nextId !== activeTrackingId) {
      setTrackingSnapshot(null)
    }
    setActiveTrackingId(nextId)
  }

  useEffect(() => {
    let active = true

    async function loadTrackingSnapshot(showLoader = true) {
      if (!activeTrackingId) {
        return
      }

      if (showLoader) {
        setTrackingLoading(true)
      }

      try {
        const snapshot = await getTrackingShipment(activeTrackingId)
        if (active) {
          setTrackingSnapshot(snapshot)
          setTrackingError('')
        }
      } catch (error) {
        if (active) {
          setTrackingError(error.message || 'Tracking lookup failed.')
        }
      } finally {
        if (active && showLoader) {
          setTrackingLoading(false)
        }
      }
    }

    if (!activeTrackingId) {
      setTrackingSnapshot(null)
      setTrackingLoading(false)
      return () => {
        active = false
      }
    }

    loadTrackingSnapshot(true)
    const pollMs = Math.max(
      5000,
      (trackingSnapshot?.poll_seconds || backendHealth?.tracking?.poll_seconds || 15) * 1000
    )
    const interval = window.setInterval(() => {
      loadTrackingSnapshot(false)
    }, pollMs)

    return () => {
      active = false
      window.clearInterval(interval)
    }
  }, [activeTrackingId, backendHealth?.tracking?.poll_seconds, trackingSnapshot?.poll_seconds])

  useEffect(() => {
    let active = true

    async function loadNews() {
      if (!routeData) {
        setNewsState(DEFAULT_NEWS_STATE)
        return
      }

      setNewsState((current) => ({
        ...current,
        status: 'loading',
      }))

      try {
        const result = await fetchGeminiOperationalNews({
          routeData,
          shipmentDate,
          simulationResult,
        })

        if (active) {
          setNewsState(result)
        }
      } catch (error) {
        if (active) {
          setNewsState({
            status: 'error',
            summary: error.message || 'Failed to load Gemini intelligence.',
            items: [],
          })
        }
      }
    }

    loadNews()
    return () => {
      active = false
    }
  }, [routeData, shipmentDate, simulationResult])

  return (
    <div className="app-shell">
      <TopBar
        serviceStatus={serviceStatus}
        routeData={routeData}
        shipmentRecord={
          trackingSnapshot
            ? { shipmentId: trackingSnapshot.shipment_id }
            : null
        }
      />

      <main className="workspace">
        <section className="panel-grid panel-grid--overview">
          <RouteAnalysisPanel
            form={routeForm}
            onFormChange={setRouteForm}
            onSubmit={handleAnalyzeRoute}
            loading={routeLoading}
            error={routeError}
            routeData={routeData}
            shipmentId={trackingSnapshot?.shipment_id}
          />
          <ModalComparisonPanel routeData={routeData} />
          <WeatherDisruptionPanel
            shipmentDate={shipmentDate}
            onShipmentDateChange={setShipmentDate}
            signals={disruptionSignals}
            selectedDisruptionId={selectedDisruptionId}
            onSelectedDisruptionIdChange={setSelectedDisruptionId}
            onSimulate={handleSimulateDisruption}
            simulationLoading={simulationLoading}
            simulationResult={simulationResult}
            simulationError={simulationError}
            routeData={routeData}
          />
          <WeatherNewsPanel
            routeData={routeData}
            newsState={newsState}
          />
        </section>

        <section className="panel-grid panel-grid--detail">
          <RecommendationPanel
            routeData={routeData}
            simulationResult={simulationResult}
          />
          <RouteMapPanel routeData={routeData} />
        </section>

        <SupplyNewsAlertsPanel
          alerts={alerts}
          newsState={newsState}
          routeData={routeData}
        />

        <TrackingSection
          trackingDraftId={trackingDraftId}
          onTrackingDraftIdChange={setTrackingDraftId}
          onTrackShipment={handleTrackShipment}
          trackingSnapshot={trackingSnapshot}
          trackingLoading={trackingLoading}
          trackingError={trackingError}
        />
      </main>
    </div>
  )
}
