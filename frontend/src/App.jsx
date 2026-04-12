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
import { checkHealth, getRoute, simulateRoute } from './services/api'
import {
  fetchGeminiOperationalNews,
  getGeminiConfigState,
} from './services/gemini'
import {
  buildOperationalAlerts,
  buildWeatherTrend,
  deriveDisruptionSignals,
  getTodayDateString,
} from './utils/intelligence'
import { buildShipmentRecord, findShipmentRecord } from './utils/tracking'

const DEFAULT_FORM = {
  source: 'Mumbai',
  destination: 'Pune',
  transport_mode: 'road',
  region_type: 'tier_2',
}

const DEFAULT_NEWS_STATE = {
  status: 'idle',
  summary: '',
  items: [],
}

export default function App() {
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
  const [shipmentLookupId, setShipmentLookupId] = useState('')

  useEffect(() => {
    async function pingBackend() {
      try {
        await checkHealth()
        setBackendStatus('online')
      } catch {
        setBackendStatus('offline')
      }
    }

    pingBackend()
    const interval = window.setInterval(pingBackend, 30000)
    return () => window.clearInterval(interval)
  }, [])

  const weatherTrend = useMemo(
    () => buildWeatherTrend(routeData?.weather, shipmentDate),
    [routeData, shipmentDate]
  )

  const disruptionSignals = useMemo(
    () => deriveDisruptionSignals({ routeData, shipmentDate }),
    [routeData, shipmentDate]
  )

  const shipmentRecord = useMemo(
    () => buildShipmentRecord(routeData, shipmentDate),
    [routeData, shipmentDate]
  )

  useEffect(() => {
    if (shipmentRecord) {
      setShipmentLookupId(shipmentRecord.shipmentId)
    } else {
      setShipmentLookupId('')
    }
  }, [shipmentRecord])

  const shipmentFound = useMemo(
    () => findShipmentRecord(shipmentLookupId, shipmentRecord),
    [shipmentLookupId, shipmentRecord]
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
        newsState.status === 'ready'
          ? 'live'
          : newsState.status === 'error'
            ? 'error'
            : newsState.status === 'not_configured'
              ? 'missing'
              : getGeminiConfigState(),
    }),
    [backendStatus, newsState, routeData]
  )

  async function handleAnalyzeRoute() {
    setRouteLoading(true)
    setRouteError('')
    setSimulationResult(null)
    setSimulationError('')

    try {
      const data = await getRoute(routeForm)
      setRouteData(data)
    } catch (error) {
      setRouteData(null)
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
        shipmentRecord={shipmentRecord}
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
            shipmentId={shipmentRecord?.shipmentId}
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
            weatherTrend={weatherTrend}
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
          shipmentLookupId={shipmentLookupId}
          onShipmentLookupIdChange={setShipmentLookupId}
          shipmentRecord={shipmentRecord}
          shipmentFound={shipmentFound}
        />
      </main>
    </div>
  )
}
