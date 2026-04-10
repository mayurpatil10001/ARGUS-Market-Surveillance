/**
 * ARGUS Production API Client
 * ─────────────────────────────────────────────────────────────────────────────
 * - JWT token stored ONLY in memory (never localStorage / sessionStorage)
 * - Authenticates eagerly at module load
 * - De-duplicates concurrent auth requests (single in-flight promise)
 * - Auto-refreshes token on 401, retries original request once
 * - Returns null on all failures — never throws to caller/UI
 */

const BASE_URL = import.meta.env.VITE_API_URL || 'http://127.0.0.1:8080'
const ADMIN_PW  = import.meta.env.VITE_ADMIN_PASSWORD || 'argus2024'

let _token       = null   // in-memory only
let _tokenFlight = null   // de-duplicate parallel logins

async function login() {
  const body = new URLSearchParams()
  body.append('username', 'admin')
  body.append('password', ADMIN_PW)
  const res = await fetch(`${BASE_URL}/auth/token`, { method: 'POST', body })
  if (!res.ok) throw new Error(`[ARGUS] Auth failed ${res.status}`)
  const { access_token } = await res.json()
  _token = access_token
  return _token
}

export async function getToken() {
  if (_token) return _token
  if (_tokenFlight) return _tokenFlight
  _tokenFlight = login().finally(() => { _tokenFlight = null })
  return _tokenFlight
}

// Eagerly authenticate on module load so first data request is instant
getToken().catch(e => console.warn('[ARGUS] Initial auth failed:', e.message))

// ─── Core fetch wrapper ───────────────────────────────────────────────────────

async function req(path, options = {}) {
  let token = await getToken().catch(() => null)

  const buildHeaders = (t) => ({
    'Content-Type': 'application/json',
    ...options.headers,
    ...(t ? { Authorization: `Bearer ${t}` } : {}),
  })

  const doFetch = (t) =>
    fetch(`${BASE_URL}${path}`, { ...options, headers: buildHeaders(t) })

  try {
    let res = await doFetch(token)

    if (res.status === 401) {
      // Force refresh once
      _token = null
      token = await getToken().catch(() => null)
      if (!token) return null
      res = await doFetch(token)
    }

    if (!res.ok) {
      console.warn(`[ARGUS API] ${options.method || 'GET'} ${path} → ${res.status}`)
      return null
    }

    if (res.status === 204) return { ok: true }
    return res.json()
  } catch (err) {
    console.warn(`[ARGUS API] Network error on ${path}:`, err.message)
    return null
  }
}

function get(path, params) {
  const entries = Object.entries(params || {}).filter(([, v]) => v != null && v !== '')
  const qs = entries.length ? '?' + new URLSearchParams(entries) : ''
  return req(`${path}${qs}`)
}

function post(path, body) {
  return req(path, { method: 'POST', body: JSON.stringify(body) })
}

// ─── Public API surface ───────────────────────────────────────────────────────

export const argusApi = {
  /** System */
  health: () => get('/health'),

  /** Alerts */
  getAlerts:         (params)                    => get('/alerts', params),
  getAlert:          (id)                        => get(`/alerts/${id}`),
  updateAlertStatus: (id, status)                => post(`/alerts/${id}/status`, { status }),
  assignAlert:       (id, analyst)               => post(`/alerts/${id}/assign`, { analyst }),

  /** Accounts */
  searchAccounts:    (params)                    => get('/accounts/search', params),
  getAccountDNA:     (id)                        => get(`/accounts/${id}/dna`),
  getAccountTrades:  (id, params)                => get(`/accounts/${id}/trades`, params),
  getAccountNetwork: (id)                        => get(`/accounts/${id}/network`),

  /** Reports */
  generateCase:      (alertId, payload)          => post(`/reports/case/${alertId}`, payload),
  getWeeklySummary:  ()                          => get('/reports/summary/weekly'),
  downloadCaseUrl:   (alertId)                   => `${BASE_URL}/reports/case/${alertId}/download`,

  /** Mitigation */
  getMitigationSummary: ()                       => get('/alerts/mitigation/summary'),
  getMitigationPending: (severity)               =>
    get('/alerts/mitigation/pending', severity && severity !== 'all' ? { severity } : {}),
  applyMitigation:   (id, action = 'monitor_and_log', notes = '') =>
    post(`/alerts/${id}/mitigate`, { action, applied_by: 'analyst', notes }),
  dismissMitigation: (id, reason = 'Dismissed by analyst') =>
    post(`/alerts/${id}/dismiss-mitigation`, { dismissed_by: 'analyst', reason }),
  escalateAlert:     (id) =>
    post(`/alerts/${id}/escalate`, { escalated_by: 'analyst' }),
}

// ─── SSE Live Alert Stream ────────────────────────────────────────────────────

/**
 * Opens an SSE connection to /alerts/live.
 * Auto-reconnects on error with 5-second backoff.
 * Returns a cleanup function.
 */
export function connectLiveAlerts(onAlert) {
  let es         = null
  let retryTimer = null
  let destroyed  = false

  async function connect() {
    if (destroyed) return
    const token = await getToken().catch(() => null)
    if (!token) {
      retryTimer = setTimeout(connect, 5000)
      return
    }
    es = new EventSource(`${BASE_URL}/alerts/live?token=${encodeURIComponent(token)}`)
    es.onmessage = (e) => {
      try {
        const msg = JSON.parse(e.data)
        // Backend wraps alerts as { type: 'alert', data: { ...alert } }
        if (msg?.type === 'alert' && msg?.data) {
          onAlert(msg.data)
        } else if (msg?.type === 'connected') {
          console.info('[ARGUS SSE] Stream connected at', msg.timestamp)
        }
      } catch {}
    }
    es.onerror = () => {
      es.close()
      es = null
      if (!destroyed) retryTimer = setTimeout(connect, 5000)
    }
  }

  connect()

  return () => {
    destroyed = true
    clearTimeout(retryTimer)
    es?.close()
  }
}
