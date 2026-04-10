/**
 * src/api/client.js — Backward-compatible adapter over src/lib/api.js
 *
 * All existing components continue importing from './api/client' unchanged.
 * Token is now stored in memory only (never localStorage).
 * Mock mode is gone — all calls go to the real FastAPI backend.
 *
 * Shape normalisation:
 *  - GET /alerts  → plain list[]  → wrapped as { alerts: [], total: N }
 *  - GET /health  → { status, services, model_versions } → normalised for Sidebar
 */
import { argusApi, connectLiveAlerts, getToken } from '../lib/api'

// Re-export SSE helper (some components import it directly from here)
export { connectLiveAlerts }

// ── Alerts: backend returns plain list, UI expects { alerts, total } ───────────
async function getAlerts(params) {
  const raw = await argusApi.getAlerts(params)
  if (!raw) return { data: { alerts: [], total: 0 } }
  // Backend may return plain list OR already-wrapped object (future proofing)
  const list = Array.isArray(raw) ? raw : raw.alerts || []
  return { data: { alerts: list, total: list.length } }
}

// ── Health: normalise service/model keys for Sidebar ───────────────────────────
async function health() {
  const raw = await argusApi.health()
  if (!raw) return { data: null }
  // Map backend shape → shape Sidebar expects:
  //   raw.services.db       → data.database.status
  //   raw.model_versions.*  → data.models.*.loaded (bool)
  const mv = raw.model_versions || {}
  return {
    data: {
      status: raw.status,
      database: { status: raw.services?.db === 'ok' ? 'ok' : raw.services?.postgres === 'ok' ? 'ok' : 'error' },
      redis:    { status: raw.services?.redis || 'unknown' },
      models: {
        gnn:          { loaded: mv.tcn === 'loaded' },
        dna:          { loaded: mv.autoencoder === 'loaded' },
        cross_market: { loaded: mv.fingerprint_store === 'loaded' },
        zero_day:     { loaded: mv.zero_day === 'loaded' },
      },
    },
  }
}

export const api = {
  // ── Health ──────────────────────────────────────────────────────────────────
  health,

  // ── Alerts ──────────────────────────────────────────────────────────────────
  getAlerts,
  getAlert: async (id) => ({ data: await argusApi.getAlert(id) }),
  updateAlertStatus: async (id, status) => {
    await argusApi.updateAlertStatus(id, status)
    return { data: { ok: true } }
  },
  assignAlert: async (id, analyst) => {
    await argusApi.assignAlert(id, analyst)
    return { data: { ok: true } }
  },

  // ── Accounts ─────────────────────────────────────────────────────────────────
  searchAccounts:    async (p) => ({ data: await argusApi.searchAccounts(p) }),
  getAccountDNA:     async (id) => ({ data: await argusApi.getAccountDNA(id) }),
  getAccountTrades:  async (id, p) => ({ data: await argusApi.getAccountTrades(id, p) }),
  getAccountNetwork: async (id) => ({ data: await argusApi.getAccountNetwork(id) }),
  getNetworkForAccounts: async (id) => ({ data: await argusApi.getAccountNetwork(id) }),

  // ── Reports ──────────────────────────────────────────────────────────────────
  generateCase:  async (alertId, payload) => ({ data: await argusApi.generateCase(alertId, payload) }),
  weeklySummary: async () => ({ data: await argusApi.getWeeklySummary() }),
  downloadCase:  (alertId) => argusApi.downloadCaseUrl(alertId),

  // ── Mitigation ───────────────────────────────────────────────────────────────
  getMitigationSummary: async () => ({ data: await argusApi.getMitigationSummary() }),
  getMitigationPending: async (sev) => ({ data: await argusApi.getMitigationPending(sev) }),
  mitigateAlert: async (id, action, _by, notes = '') => {
    await argusApi.applyMitigation(id, action, notes)
    return { data: { ok: true } }
  },
  dismissMitigation: async (id, _by, reason) => {
    await argusApi.dismissMitigation(id, reason)
    return { data: { ok: true } }
  },
  escalateAlert: async (id) => {
    await argusApi.escalateAlert(id)
    return { data: { ok: true } }
  },
}
