import axios from 'axios'
import {
  mockAlerts, mockAccounts, mockTrades,
  mockNetwork23, mockWeeklySummary, mockHealth,
  mockMitigationSummary, mockPendingMitigations,
} from './mockData'

const BASE_URL = import.meta.env.VITE_API_URL || 'http://127.0.0.1:8080'
const USE_MOCK  = import.meta.env.VITE_USE_MOCK === 'true'

const delay = (ms=300) => new Promise(r => setTimeout(r, ms))

const client = axios.create({ baseURL: BASE_URL })

client.interceptors.request.use(cfg => {
  const token = localStorage.getItem('argus_token')
  if (token) cfg.headers.Authorization = `Bearer ${token}`
  return cfg
})

client.interceptors.response.use(
  res => res,
  async err => {
    if (err.response?.status === 401) {
      try {
        const params = new URLSearchParams()
        params.append('username', 'admin')
        params.append('password', import.meta.env.VITE_ADMIN_PASSWORD || 'argus2024')
        const r = await axios.post(`${BASE_URL}/auth/token`, params)
        localStorage.setItem('argus_token', r.data.access_token)
        err.config.headers.Authorization = `Bearer ${r.data.access_token}`
        return client.request(err.config)
      } catch { return Promise.reject(err) }
    }
    return Promise.reject(err)
  }
)

export const api = {
  health: async () => {
    if (USE_MOCK) { await delay(200); return { data: mockHealth } }
    return client.get('/health')
  },

  getAlerts: async (params) => {
    if (USE_MOCK) {
      await delay(400)
      let alerts = [...mockAlerts]
      if (params?.status && params.status !== 'all')
        alerts = alerts.filter(a => a.status === params.status)
      if (params?.min_score)
        alerts = alerts.filter(a => a.impossibility_score >= Number(params.min_score))
      if (params?.scrip)
        alerts = alerts.filter(a => a.scrip.toLowerCase().includes(params.scrip.toLowerCase()))
      alerts.sort((a,b) => b.impossibility_score - a.impossibility_score)
      return { data: { alerts, total: alerts.length } }
    }
    return client.get('/alerts', { params })
  },

  getAlert: async (id) => {
    if (USE_MOCK) {
      await delay(200)
      const a = mockAlerts.find(a => a.id === id)
      return { data: a }
    }
    return client.get(`/alerts/${id}`)
  },

  updateAlertStatus: async (id, status) => {
    if (USE_MOCK) { await delay(300); return { data: { ok: true } } }
    return client.post(`/alerts/${id}/status`, { status })
  },

  searchAccounts: async (params) => {
    if (USE_MOCK) {
      await delay(500)
      const accs = Object.values(mockAccounts)
      return { data: { accounts: accs } }
    }
    return client.get('/accounts/search', { params })
  },

  getAccountDNA: async (id) => {
    if (USE_MOCK) {
      await delay(600)
      const acc = mockAccounts[id] || mockAccounts[Object.keys(mockAccounts)[0]]
      return { data: acc }
    }
    return client.get(`/accounts/${id}/dna`)
  },

  getAccountTrades: async (id, params) => {
    if (USE_MOCK) {
      await delay(400)
      const trades = mockTrades[id] || mockTrades[Object.keys(mockTrades)[0]]
      return { data: { trades } }
    }
    return client.get(`/accounts/${id}/trades`, { params })
  },

  getAccountNetwork: async (id) => {
    if (USE_MOCK) {
      await delay(700)
      return { data: mockNetwork23 }
    }
    return client.get(`/accounts/${id}/network`)
  },

  generateCase: async (alertId, data) => {
    if (USE_MOCK) {
      await delay(1500)
      const caseNum = `ARGUS/2026/${Math.random().toString(36).slice(2,10).toUpperCase()}`
      return { data: { case_number: caseNum, pdf_url: '#', file_size_kb: 284 } }
    }
    return client.post(`/reports/case/${alertId}`, data)
  },

  downloadCase: (alertId) => `${BASE_URL}/reports/case/${alertId}/download`,

  weeklySummary: async () => {
    if (USE_MOCK) { await delay(500); return { data: mockWeeklySummary } }
    return client.get('/reports/summary/weekly')
  },

  getNetworkForAccounts: async (params) => {
    if (USE_MOCK) { await delay(800); return { data: mockNetwork23 } }
    return client.get('/network', { params })
  },

  mitigateAlert: async (id, action, appliedBy = 'analyst', notes = '') => {
    if (USE_MOCK) { await delay(300); return { data: { ok: true } } }
    return client.post(`/alerts/${id}/mitigate`, { action, applied_by: appliedBy, notes })
  },

  dismissMitigation: async (id, dismissedBy = 'analyst', reason = 'Dismissed by analyst') => {
    if (USE_MOCK) { await delay(300); return { data: { ok: true } } }
    return client.post(`/alerts/${id}/dismiss-mitigation`, { dismissed_by: dismissedBy, reason })
  },

  escalateAlert: async (id, escalatedBy = 'analyst') => {
    if (USE_MOCK) { await delay(300); return { data: { ok: true } } }
    return client.post(`/alerts/${id}/escalate`, { escalated_by: escalatedBy })
  },

  getMitigationSummary: async () => {
    if (USE_MOCK) { await delay(400); return { data: mockMitigationSummary } }
    return client.get('/alerts/mitigation/summary')
  },

  getMitigationPending: async (severity) => {
    if (USE_MOCK) {
      await delay(400)
      let list = [...mockPendingMitigations]
      if (severity && severity !== 'all') list = list.filter(a => a.severity === severity)
      return { data: list }
    }
    const params = severity && severity !== 'all' ? { severity } : {}
    return client.get('/alerts/mitigation/pending', { params })
  },
}

export function connectLiveAlerts(onAlert) {
  if (USE_MOCK) {
    // Simulate occasional new alerts in mock mode
    const schemes = ['pump_and_dump','spoofing','circular_trading']
    const scrips  = ['ALERT_TEST','MOCK_SCRIP_A','DEMO_NEW']
    const id = setInterval(() => {
      if (Math.random() > 0.7) {
        onAlert({
          id: `mock_${Date.now()}`,
          scrip: scrips[Math.floor(Math.random()*3)],
          exchange: 'NSE',
          detected_at: new Date().toISOString(),
          impossibility_score: (7 + Math.random() * 3).toFixed(1),
          scheme_type: schemes[Math.floor(Math.random()*3)],
          status: 'open',
          accounts_involved: [],
          gnn_score: 7.5, dna_score: 8.0, cross_market_score: 6.0, zero_day_score: 8.5,
        })
      }
    }, 15000)
    return () => clearInterval(id)
  }
  const token = localStorage.getItem('argus_token')
  const es = new EventSource(`${BASE_URL}/alerts/live?token=${token}`)
  es.onmessage = e => { try { onAlert(JSON.parse(e.data)) } catch {} }
  es.onerror = () => setTimeout(() => connectLiveAlerts(onAlert), 5000)
  return () => es.close()
}
