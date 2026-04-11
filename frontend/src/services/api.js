import axios from 'axios'

const BASE_URL = import.meta.env.VITE_API_BASE_URL || 'http://127.0.0.1:5000'

const api = axios.create({
  baseURL: BASE_URL,
  timeout: 15000,
  headers: { 'Content-Type': 'application/json' },
})

api.interceptors.response.use(
  (res) => {
    if (res.data && res.data.success === false) {
      return Promise.reject(new Error(res.data.error || 'Request failed'))
    }
    return res
  },
  (err) => {
    const msg =
      err.response?.data?.error ||
      err.message ||
      'Network error'
    return Promise.reject(new Error(msg))
  }
)

const DISRUPTION_MAP = {
  'Heavy rainfall in a region': {
    backendValue: 'heavy rainfall in a region',
    note: '',
  },
  'Port congestion or delays': {
    backendValue: 'port congestion or delays',
    note: '',
  },
  'Increased demand in Tier-2 cities': {
    backendValue: 'increased demand in tier-2 cities',
    note: '',
  },
  'Route blockage due to regulatory or operational issues': {
    backendValue: 'route blockage due to regulatory or operational issues',
    note: '',
  },
}

export const checkHealth = async () => {
  const res = await api.get('/health')
  return res.data.data
}

export const getRoute = async ({ source, destination, transport_mode, region_type }) => {
  const res = await api.post('/get-route', {
    source,
    destination,
    transport_mode,
    region_type,
  })
  return res.data.data
}

export const runSimulation = async ({ route, disruptionLabel }) => {
  const meta = DISRUPTION_MAP[disruptionLabel] || DISRUPTION_MAP['Heavy rainfall in a region']
  const res = await api.post('/simulate', {
    route,
    disruption_type: meta.backendValue,
  })
  return {
    ...res.data.data,
    requested_disruption_label: disruptionLabel,
    scenario_modeling_note: res.data.data?.scenario_modeling_note || meta.note,
  }
}
