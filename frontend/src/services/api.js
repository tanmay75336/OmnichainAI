import axios from 'axios'

export const API_BASE_URL =
  import.meta.env.VITE_API_BASE_URL || 'http://127.0.0.1:5000'

const api = axios.create({
  baseURL: API_BASE_URL,
  timeout: 20000,
  headers: { 'Content-Type': 'application/json' },
})

api.interceptors.response.use(
  (response) => {
    if (response.data?.success === false) {
      return Promise.reject(new Error(response.data.error || 'Request failed'))
    }
    return response
  },
  (error) => {
    const message =
      error.response?.data?.error ||
      error.message ||
      'Network request failed.'
    return Promise.reject(new Error(message))
  }
)

export const DISRUPTION_CATALOG = {
  monsoon: {
    id: 'monsoon',
    label: 'Monsoon Pressure',
    backendValue: 'monsoon',
    severity: 'high',
    summary: 'Models heavy rain exposure across the route corridor.',
    backendMapping: 'monsoon -> heavy_rainfall',
  },
  flood: {
    id: 'flood',
    label: 'Flood Corridor',
    backendValue: 'flood',
    severity: 'high',
    summary: 'Models acute waterlogging and route slowdown on exposed links.',
    backendMapping: 'flood -> heavy_rainfall',
  },
  political: {
    id: 'political',
    label: 'Political / Strike',
    backendValue: 'strike',
    severity: 'medium',
    summary: 'Models operational stoppage, strike, or regulatory route blockage.',
    backendMapping: 'political -> route_blockage',
  },
  holiday: {
    id: 'holiday',
    label: 'Holiday Congestion',
    backendValue: 'government holiday',
    severity: 'medium',
    summary: 'Models reduced throughput, holiday staffing pressure, and gate delays.',
    backendMapping: 'holiday -> demand_spike',
  },
}

export async function checkHealth() {
  const response = await api.get('/health')
  return response.data.data
}

export async function getRoute(payload) {
  const response = await api.post('/get-route', payload)
  return response.data.data
}

export async function simulateRoute({ route, disruptionId }) {
  const disruption = DISRUPTION_CATALOG[disruptionId] || DISRUPTION_CATALOG.monsoon
  const response = await api.post('/simulate', {
    route,
    disruption_type: disruption.backendValue,
  })

  return {
    ...response.data.data,
    requested_disruption_label:
      response.data.data?.requested_disruption_label || disruption.label,
    disruption_id: disruption.id,
    disruption_label: disruption.label,
    backend_mapping: disruption.backendMapping,
    scenario_modeling_note:
      response.data.data?.scenario_modeling_note ||
      `${disruption.backendMapping}.`,
  }
}
