import { useState, useEffect, useRef } from 'react'
import { useQuery, useQueryClient } from 'react-query'
import { motion, AnimatePresence } from 'framer-motion'
import toast from 'react-hot-toast'
import { api, connectLiveAlerts } from '../api/client'
import MetricCard from '../components/MetricCard'
import CaseModal  from '../components/CaseModal'

// ─── Scheme config ─────────────────────────────────────────────────────────────
const SCHEME_CFG = {
  pump_and_dump:    { color: '#ef4444', label: 'PUMP & DUMP' },
  spoofing:         { color: '#f59e0b', label: 'SPOOFING' },
  layering:         { color: '#f59e0b', label: 'LAYERING' },
  circular_trading: { color: '#a855f7', label: 'CIRCULAR' },
  insider_trading:  { color: '#f97316', label: 'INSIDER' },
  wash_trading:     { color: '#6366f1', label: 'WASH TRADE' },
  front_running:    { color: '#ec4899', label: 'FRONT RUN' },
  painting_tape:    { color: '#84cc16', label: 'PAINT TAPE' },
  churning:         { color: '#14b8a6', label: 'CHURNING' },
  social_media_pump:{ color: '#22d3ee', label: 'SOCIAL PUMP' },
  misinformation:   { color: '#84cc16', label: 'MISINFO' },
  phishing:         { color: '#ef4444', label: 'PHISHING' },
}

function getSchemeCfg(key) {
  return SCHEME_CFG[key] || { color: '#71717a', label: (key || 'UNKNOWN').replace(/_/g, ' ').toUpperCase() }
}

// ─── Status config ──────────────────────────────────────────────────────────────
const STATUS_CFG = {
  open:           { color: '#f59e0b', label: 'OPEN' },
  investigating:  { color: '#22d3ee', label: 'INVESTIGATING' },
  closed:         { color: '#10b981', label: 'RESOLVED' },
  false_positive: { color: '#71717a', label: 'FALSE POS' },
}

function getStatusCfg(key) {
  return STATUS_CFG[key] || { color: '#71717a', label: (key || 'UNKNOWN').toUpperCase() }
}

// ─── Sub-components ─────────────────────────────────────────────────────────────
function SchemeBadge({ scheme }) {
  const { color, label } = getSchemeCfg(scheme)
  return (
    <span style={{
      display: 'inline-block',
      padding: '2px 7px',
      background: color + '18',
      border: `1px solid ${color}55`,
      borderRadius: 4,
      color,
      fontFamily: 'var(--font-mono)',
      fontSize: 9,
      fontWeight: 700,
      letterSpacing: 0.8,
      whiteSpace: 'nowrap',
    }}>
      {label}
    </span>
  )
}

function StatusBadge({ status }) {
  const { color, label } = getStatusCfg(status)
  return (
    <span style={{
      display: 'inline-block',
      padding: '2px 8px',
      background: color + '18',
      border: `1px solid ${color}55`,
      borderRadius: 4,
      color,
      fontFamily: 'var(--font-mono)',
      fontSize: 9,
      fontWeight: 700,
      letterSpacing: 0.8,
    }}>
      {label}
    </span>
  )
}

function ScoreCell({ score }) {
  const s = Number(score) || 0
  const pct = Math.min(100, (s / 10) * 100)
  const color = s >= 9 ? 'var(--accent-red)' : s >= 7.5 ? 'var(--accent-amber)' : 'var(--accent-green)'
  return (
    <div>
      <span style={{
        fontFamily: 'var(--font-mono)', fontSize: 14,
        fontWeight: 700, color,
        animation: s >= 9 ? 'sev-pulse 2s ease-in-out infinite' : 'none',
      }}>
        {s.toFixed(1)}
      </span>
      <div style={{
        height: 2, background: 'var(--border)',
        marginTop: 4, borderRadius: 1,
      }}>
        <div style={{
          width: `${pct}%`, height: '100%',
          background: color, borderRadius: 1,
          transition: 'width 0.4s',
        }} />
      </div>
    </div>
  )
}

function ActionBtn({ children, color, onClick, disabled }) {
  return (
    <button
      onClick={onClick}
      disabled={disabled}
      style={{
        padding: '5px 10px',
        background: 'transparent',
        border: `1px solid ${color}`,
        color,
        fontFamily: 'var(--font-mono)',
        fontSize: 9,
        letterSpacing: 1,
        cursor: disabled ? 'not-allowed' : 'pointer',
        borderRadius: 4,
        opacity: disabled ? 0.4 : 1,
        whiteSpace: 'nowrap',
        transition: 'background 0.15s',
      }}
      onMouseEnter={e => !disabled && (e.currentTarget.style.background = color + '18')}
      onMouseLeave={e => !disabled && (e.currentTarget.style.background = 'transparent')}
    >
      {children}
    </button>
  )
}

// ─── Skeleton rows ──────────────────────────────────────────────────────────────
const COL = '90px 150px 120px 80px 80px 130px 1fr'

function SkeletonRows({ n = 6 }) {
  return (
    <>
      {Array.from({ length: n }).map((_, i) => (
        <div key={i} style={{
          display: 'grid', gridTemplateColumns: COL,
          padding: '12px 16px', gap: 12,
          borderBottom: '1px solid var(--border)',
          alignItems: 'center',
        }}>
          {[55, 110, 90, 55, 55, 80, 120].map((w, j) => (
            <div key={j} className="skeleton" style={{ height: 11, width: `${w}%` }} />
          ))}
        </div>
      ))}
    </>
  )
}

// ─── Engine score row (expanded detail) ────────────────────────────────────────
const ENGINE_SCORES = [
  { key: 'gnn_score',         label: 'GNN / TCN',     scale: 10  },
  { key: 'dna_score',         label: 'DNA',            scale: 10  },
  { key: 'cross_market_score',label: 'Cross-Market',   scale: 10  },
  { key: 'zero_day_score',    label: 'Zero-Day',       scale: 10  },
  { key: 'social_signal_score',label: 'Social Signal', scale: 1   },
  { key: 'misinfo_score',     label: 'Misinformation', scale: 1   },
]

function EngineScoreBar({ label, val, scale }) {
  const v   = Number(val) || 0
  const pct = Math.min(100, (v / scale) * 100)
  const norm = v / scale          // 0-1
  const color = norm >= 0.9 ? 'var(--accent-red)'
              : norm >= 0.75 ? 'var(--accent-amber)'
              : 'var(--accent-green)'
  return (
    <div style={{ display: 'flex', alignItems: 'center', gap: 10, marginBottom: 5 }}>
      <div style={{
        fontFamily: 'var(--font-mono)', fontSize: 9,
        color: 'var(--text-secondary)', width: 100, flexShrink: 0,
      }}>{label}</div>
      <div style={{ flex: 1, height: 3, background: 'var(--border)', borderRadius: 2 }}>
        <div style={{ width: `${pct}%`, height: '100%', background: color, borderRadius: 2 }} />
      </div>
      <div style={{
        fontFamily: 'var(--font-mono)', fontSize: 9,
        color: 'var(--text-primary)', width: 32, textAlign: 'right',
      }}>
        {(v * (scale === 1 ? 10 : 1)).toFixed(1)}
      </div>
    </div>
  )
}

// ─── Main page ──────────────────────────────────────────────────────────────────
const TABLE_HEADERS = ['SCORE', 'SCHEME', 'SCRIP', 'ACCOUNTS', 'TIME (UTC)', 'STATUS', 'ACTIONS']
const PER_PAGE = 10

export default function LiveAlerts() {
  const [filters, setFilters] = useState({ scrip: '', status: 'all', min_score: 0 })
  const [page, setPage]       = useState(1)
  const [newIds, setNewIds]   = useState(new Set())
  const [expandId, setExpandId] = useState(null)
  const [caseAlert, setCaseAlert] = useState(null)
  const [actionLoading, setActionLoading] = useState({})
  const qc = useQueryClient()

  // ── Data fetch (polls every 30s via react-query defaultOptions) ──────────────
  const { data, isLoading, isError, refetch } = useQuery(
    ['alerts', filters],
    () => api.getAlerts({
      scrip:     filters.scrip    || undefined,
      status:    filters.status   === 'all' ? undefined : filters.status,
      min_score: filters.min_score > 0      ? filters.min_score : undefined,
    }),
    { select: r => r.data }
  )

  // ── SSE live stream ──────────────────────────────────────────────────────────
  useEffect(() => {
    const disconnect = connectLiveAlerts((alert) => {
      setNewIds(s => new Set([...s, alert.id]))
      toast.success(
        `NEW ALERT: ${alert.scrip} — ${Number(alert.impossibility_score).toFixed(1)}/10`,
        { duration: 5000 }
      )
      refetch()
      setTimeout(() => setNewIds(s => { const n = new Set(s); n.delete(alert.id); return n }), 3000)
    })
    return disconnect
  }, []) // eslint-disable-line

  // ── Derived values ───────────────────────────────────────────────────────────
  const alerts       = data?.alerts || (Array.isArray(data) ? data : [])
  const total        = data?.total  || alerts.length
  const critical     = alerts.filter(a => Number(a.impossibility_score) >= 9).length
  const investigating = alerts.filter(a => a.status === 'investigating').length
  const resolved     = alerts.filter(a => a.status === 'closed').length

  const paged = alerts.slice((page - 1) * PER_PAGE, page * PER_PAGE)
  const pages = Math.ceil(alerts.length / PER_PAGE)

  // ── Action handlers ──────────────────────────────────────────────────────────
  async function doAction(alertId, fn, label) {
    setActionLoading(s => ({ ...s, [alertId]: true }))
    try {
      await fn()
      toast.success(label)
      qc.invalidateQueries(['alerts'])
    } catch {
      toast.error(`Failed: ${label}`)
    } finally {
      setActionLoading(s => ({ ...s, [alertId]: false }))
    }
  }

  const handleInvestigate = (a) =>
    doAction(a.id, () => api.updateAlertStatus(a.id, 'investigating'), `${a.scrip} → INVESTIGATING`)

  const handleDismiss = (a) =>
    doAction(a.id, () => api.updateAlertStatus(a.id, 'false_positive'), `${a.scrip} → FALSE POSITIVE`)

  // ── Filter helpers ───────────────────────────────────────────────────────────
  const setFilter = (key, val) => { setFilters(f => ({ ...f, [key]: val })); setPage(1) }

  return (
    <motion.div
      initial={{ opacity: 0, y: -6 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.18 }}
    >
      <style>{`
        @keyframes sev-pulse {
          0%,100% { text-shadow: none; }
          50%      { text-shadow: 0 0 8px rgba(239,68,68,0.7); }
        }
      `}</style>

      {/* ── KPI Cards ─────────────────────────────────────────────────── */}
      <div style={{
        display: 'grid', gridTemplateColumns: 'repeat(4,1fr)',
        gap: 14, marginBottom: 22,
      }}>
        <MetricCard label="Total Alerts"   value={total}        color="var(--text-secondary)" />
        <MetricCard label="Critical ≥ 9"   value={critical}     color="var(--accent-red)" />
        <MetricCard label="Investigating"  value={investigating} color="var(--accent-green)" />
        <MetricCard label="Resolved"       value={resolved}      color="var(--accent-amber)" />
      </div>

      {/* ── Filter bar ────────────────────────────────────────────────── */}
      <div style={{
        display: 'flex', gap: 10, marginBottom: 14,
        alignItems: 'center',
        padding: '10px 14px',
        background: 'var(--bg-card)',
        border: '1px solid var(--border)',
        borderRadius: 10,
        flexWrap: 'wrap',
      }}>
        <input
          placeholder="SEARCH SCRIP..."
          value={filters.scrip}
          onChange={e => setFilter('scrip', e.target.value)}
          style={{ flex: 1, maxWidth: 200 }}
        />
        <select
          value={filters.status}
          onChange={e => setFilter('status', e.target.value)}
          style={{ width: 160 }}
        >
          <option value="all">ALL STATUS</option>
          <option value="open">OPEN</option>
          <option value="investigating">INVESTIGATING</option>
          <option value="closed">RESOLVED</option>
          <option value="false_positive">FALSE POSITIVE</option>
        </select>
        <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
          <span style={{
            fontFamily: 'var(--font-mono)', fontSize: 9,
            color: 'var(--text-dim)', whiteSpace: 'nowrap',
          }}>
            MIN SCORE: {Number(filters.min_score).toFixed(1)}
          </span>
          <input
            type="range" min={0} max={10} step={0.5}
            value={filters.min_score}
            onChange={e => setFilter('min_score', parseFloat(e.target.value))}
            style={{ width: 90, accentColor: 'var(--accent-green)' }}
          />
        </div>
        <div style={{
          fontFamily: 'var(--font-mono)', fontSize: 9,
          color: 'var(--text-dim)', marginLeft: 'auto',
        }}>
          {total} RECORDS
        </div>
        <button
          onClick={() => refetch()}
          style={{
            padding: '6px 12px',
            background: 'transparent',
            border: '1px solid var(--border)',
            color: 'var(--text-secondary)',
            fontFamily: 'var(--font-mono)',
            fontSize: 9, letterSpacing: 1,
            borderRadius: 4,
          }}
        >
          ↻ REFRESH
        </button>
      </div>

      {/* ── Table ─────────────────────────────────────────────────────── */}
      <div style={{
        background: 'var(--bg-card)',
        border: '1px solid var(--border)',
        borderRadius: 12,
        overflow: 'hidden',
      }}>
        {/* Column headers */}
        <div style={{
          display: 'grid', gridTemplateColumns: COL,
          padding: '8px 16px', gap: 12,
          borderBottom: '1px solid var(--border-bright)',
          background: 'var(--bg-surface)',
        }}>
          {TABLE_HEADERS.map(h => (
            <div key={h} style={{
              fontFamily: 'var(--font-mono)',
              fontSize: 8, color: 'var(--text-dim)', letterSpacing: 2,
            }}>
              {h}
            </div>
          ))}
        </div>

        {/* States */}
        {isLoading && <SkeletonRows />}

        {isError && (
          <div style={{
            padding: 48, textAlign: 'center',
            fontFamily: 'var(--font-mono)', fontSize: 12,
            color: 'var(--accent-red)',
          }}>
            SYSTEM OFFLINE — BACKEND UNAVAILABLE
            <br />
            <button
              onClick={refetch}
              style={{
                marginTop: 14,
                background: 'transparent',
                border: '1px solid var(--accent-red)',
                color: 'var(--accent-red)',
                padding: '6px 18px',
                fontFamily: 'var(--font-mono)',
                fontSize: 10, cursor: 'pointer', borderRadius: 4,
              }}
            >
              RETRY →
            </button>
          </div>
        )}

        {!isLoading && !isError && paged.length === 0 && (
          <div style={{ padding: 64, textAlign: 'center' }}>
            <div style={{
              fontFamily: 'var(--font-mono)',
              fontSize: 11, letterSpacing: 2,
              color: 'var(--text-dim)',
            }}>
              NO ALERTS DETECTED — MARKET SURVEILLANCE ACTIVE
            </div>
          </div>
        )}

        {/* Alert rows */}
        {!isLoading && paged.map(alert => {
          const isNew     = newIds.has(alert.id)
          const expanded  = expandId === alert.id
          const loading   = actionLoading[alert.id]
          const ts        = alert.detected_at
            ? (() => {
                const d = new Date(alert.detected_at)
                const pad = n => String(n).padStart(2, '0')
                return `${pad(d.getUTCHours())}:${pad(d.getUTCMinutes())}`
              })()
            : '—'

          return (
            <div key={alert.id} className={isNew ? 'flash-new' : ''}>
              {/* Main row */}
              <div
                onClick={() => setExpandId(expanded ? null : alert.id)}
                style={{
                  display: 'grid', gridTemplateColumns: COL,
                  padding: '12px 16px', gap: 12,
                  borderBottom: '1px solid var(--border)',
                  alignItems: 'center',
                  cursor: 'pointer',
                  transition: 'background 0.15s',
                }}
                onMouseEnter={e => {
                  if (!isNew) e.currentTarget.style.background = 'rgba(255,255,255,0.025)'
                }}
                onMouseLeave={e => {
                  if (!isNew) e.currentTarget.style.background = 'transparent'
                }}
              >
                {/* SCORE */}
                <ScoreCell score={alert.impossibility_score} />

                {/* SCHEME */}
                <SchemeBadge scheme={alert.scheme_type} />

                {/* SCRIP */}
                <div style={{
                  fontFamily: 'var(--font-mono)', fontSize: 12,
                  fontWeight: 700, color: 'var(--text-primary)',
                  overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap',
                }}>
                  {alert.scrip}
                  <span style={{
                    fontFamily: 'var(--font-mono)', fontSize: 9,
                    color: 'var(--text-dim)', fontWeight: 400, marginLeft: 4,
                  }}>
                    {alert.exchange}
                  </span>
                </div>

                {/* ACCOUNTS */}
                <div style={{
                  fontFamily: 'var(--font-mono)', fontSize: 11,
                  color: 'var(--text-secondary)',
                }}>
                  {alert.accounts_involved?.length ?? 0}
                  <span style={{ color: 'var(--text-dim)', fontSize: 9 }}> accts</span>
                </div>

                {/* TIME UTC */}
                <div style={{
                  fontFamily: 'var(--font-mono)', fontSize: 11,
                  color: 'var(--text-dim)',
                  fontVariantNumeric: 'tabular-nums',
                }}>
                  {ts}
                </div>

                {/* STATUS */}
                <StatusBadge status={alert.status} />

                {/* ACTIONS */}
                <div
                  style={{ display: 'flex', gap: 6, alignItems: 'center' }}
                  onClick={e => e.stopPropagation()}
                >
                  <ActionBtn
                    color="var(--accent-green)"
                    onClick={() => handleInvestigate(alert)}
                    disabled={loading || alert.status === 'investigating' || alert.status === 'closed'}
                  >
                    ▷ INVESTIGATE
                  </ActionBtn>
                  <ActionBtn
                    color="var(--text-dim)"
                    onClick={() => handleDismiss(alert)}
                    disabled={loading || alert.status === 'false_positive' || alert.status === 'closed'}
                  >
                    ⊘ DISMISS
                  </ActionBtn>
                  <div style={{
                    fontSize: 10, color: 'var(--border-bright)',
                    marginLeft: 4, userSelect: 'none',
                  }}>
                    {expanded ? '▲' : '▼'}
                  </div>
                </div>
              </div>

              {/* Expanded detail panel */}
              <AnimatePresence>
                {expanded && (
                  <motion.div
                    initial={{ height: 0, opacity: 0 }}
                    animate={{ height: 'auto', opacity: 1 }}
                    exit={{ height: 0, opacity: 0 }}
                    transition={{ duration: 0.16 }}
                    style={{
                      overflow: 'hidden',
                      borderBottom: '1px solid var(--border-bright)',
                      background: 'var(--bg-surface)',
                    }}
                  >
                    <div style={{
                      padding: '16px 20px',
                      display: 'grid',
                      gridTemplateColumns: '1fr 1fr 1fr',
                      gap: 24,
                    }}>
                      {/* Engine scores */}
                      <div>
                        <div style={{
                          fontFamily: 'var(--font-mono)', fontSize: 8,
                          color: 'var(--text-dim)', letterSpacing: 2, marginBottom: 10,
                        }}>
                          ENGINE SCORES
                        </div>
                        {ENGINE_SCORES.map(({ key, label, scale }) => (
                          <EngineScoreBar
                            key={key}
                            label={label}
                            val={alert[key]}
                            scale={scale}
                          />
                        ))}
                      </div>

                      {/* Alert metadata */}
                      <div>
                        <div style={{
                          fontFamily: 'var(--font-mono)', fontSize: 8,
                          color: 'var(--text-dim)', letterSpacing: 2, marginBottom: 10,
                        }}>
                          ALERT DETAIL
                        </div>
                        {[
                          ['Alert ID',   alert.id?.slice(0, 16) + '…'],
                          ['Exchange',   alert.exchange],
                          ['Scrip',      alert.scrip],
                          ['Accounts',   alert.accounts_involved?.join(', ') || '—'],
                          ['Detected',   alert.detected_at ? new Date(alert.detected_at).toISOString().replace('T', ' ').slice(0, 16) + ' UTC' : '—'],
                          ['Auto-Mit',   alert.auto_mitigated ? '✓ YES' : 'NO'],
                          ['SEBI Esc.',  alert.escalated_to_sebi ? '✓ YES' : 'NO'],
                        ].map(([k, v]) => (
                          <div key={k} style={{
                            display: 'flex', gap: 10, marginBottom: 5,
                          }}>
                            <span style={{
                              fontFamily: 'var(--font-mono)', fontSize: 9,
                              color: 'var(--text-dim)', width: 80, flexShrink: 0,
                            }}>{k}</span>
                            <span style={{
                              fontFamily: 'var(--font-mono)', fontSize: 9,
                              color: 'var(--text-secondary)',
                              overflow: 'hidden', textOverflow: 'ellipsis',
                            }}>{v ?? '—'}</span>
                          </div>
                        ))}
                      </div>

                      {/* Extra actions */}
                      <div>
                        <div style={{
                          fontFamily: 'var(--font-mono)', fontSize: 8,
                          color: 'var(--text-dim)', letterSpacing: 2, marginBottom: 10,
                        }}>
                          FURTHER ACTIONS
                        </div>
                        <div style={{ display: 'flex', flexDirection: 'column', gap: 8 }}>
                          <ActionBtn
                            color="var(--accent-red)"
                            onClick={() => doAction(
                              alert.id,
                              () => api.escalateAlert(alert.id),
                              `${alert.scrip} escalated to SEBI`
                            )}
                            disabled={actionLoading[alert.id] || !!alert.escalated_to_sebi}
                          >
                            ▲ ESCALATE TO SEBI
                          </ActionBtn>
                          <ActionBtn
                            color="var(--accent-blue)"
                            onClick={() => setCaseAlert(alert)}
                          >
                            ⬡ GENERATE CASE PDF
                          </ActionBtn>
                        </div>
                        {alert.mitigation_notes && (
                          <div style={{
                            marginTop: 12,
                            fontFamily: 'var(--font-mono)',
                            fontSize: 9,
                            color: 'var(--text-dim)',
                            lineHeight: 1.6,
                          }}>
                            {alert.mitigation_notes.length > 140
                              ? alert.mitigation_notes.slice(0, 140) + '…'
                              : alert.mitigation_notes}
                          </div>
                        )}
                      </div>
                    </div>
                  </motion.div>
                )}
              </AnimatePresence>
            </div>
          )
        })}
      </div>

      {/* ── Pagination ────────────────────────────────────────────────── */}
      {pages > 1 && (
        <div style={{
          display: 'flex', gap: 6,
          justifyContent: 'center', marginTop: 16,
        }}>
          <button
            onClick={() => setPage(p => Math.max(1, p - 1))}
            disabled={page === 1}
            style={{
              padding: '5px 12px',
              background: 'transparent',
              border: '1px solid var(--border)',
              color: 'var(--text-secondary)',
              fontFamily: 'var(--font-mono)', fontSize: 10, borderRadius: 4,
            }}
          >
            ‹ PREV
          </button>
          {Array.from({ length: pages }, (_, i) => i + 1).map(n => (
            <button
              key={n}
              onClick={() => setPage(n)}
              style={{
                width: 32, height: 32,
                background: page === n ? 'var(--accent-green)' : 'transparent',
                color: page === n ? '#000' : 'var(--text-secondary)',
                border: `1px solid ${page === n ? 'var(--accent-green)' : 'var(--border)'}`,
                fontFamily: 'var(--font-mono)', fontSize: 10,
                borderRadius: 4,
              }}
            >
              {n}
            </button>
          ))}
          <button
            onClick={() => setPage(p => Math.min(pages, p + 1))}
            disabled={page === pages}
            style={{
              padding: '5px 12px',
              background: 'transparent',
              border: '1px solid var(--border)',
              color: 'var(--text-secondary)',
              fontFamily: 'var(--font-mono)', fontSize: 10, borderRadius: 4,
            }}
          >
            NEXT ›
          </button>
        </div>
      )}

      {/* ── Case modal ────────────────────────────────────────────────── */}
      {caseAlert && (
        <CaseModal
          alert={caseAlert}
          onClose={() => setCaseAlert(null)}
          onGenerated={() => setCaseAlert(null)}
        />
      )}
    </motion.div>
  )
}
