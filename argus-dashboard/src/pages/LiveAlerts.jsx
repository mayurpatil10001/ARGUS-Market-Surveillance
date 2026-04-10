import { useState, useEffect, useRef } from 'react'
import { useQuery, useQueryClient } from 'react-query'
import { motion, AnimatePresence } from 'framer-motion'
import toast from 'react-hot-toast'
import { api, connectLiveAlerts } from '../api/client'
import MetricCard from '../components/MetricCard'
import AlertRow from '../components/AlertRow'
import CaseModal from '../components/CaseModal'

const SEV_COLORS = {
  critical: { bg: 'rgba(255,51,85,0.15)', border: '#ff3355', text: '#ff3355', pulse: true },
  high:     { bg: 'rgba(255,140,0,0.13)',  border: '#ff8c00', text: '#ff8c00', pulse: false },
  medium:   { bg: 'rgba(255,179,0,0.12)',  border: '#ffb300', text: '#ffb300', pulse: false },
  low:      { bg: 'rgba(76,175,80,0.1)',   border: '#4caf50', text: '#4caf50', pulse: false },
}

const ACTION_LABELS = {
  freeze_accounts_and_escalate_sebi: 'FREEZE + ESCALATE',
  freeze_accounts_pending_review:    'FREEZE ACCOUNTS',
  flag_accounts_for_investigation:   'FLAG INVESTIGATE',
  block_social_signals_and_alert_compliance: 'BLOCK SOCIAL',
  flag_content_and_notify_exchange:  'FLAG CONTENT',
  block_domain_and_alert_users:      'BLOCK DOMAIN',
  isolate_entity_and_escalate:       'ISOLATE + ESCALATE',
  flag_entity_for_review:            'FLAG ENTITY',
  monitor_and_log:                   'MONITOR',
}

const MIT_STATUS_COLORS = {
  pending:   '#ffb300',
  applied:   '#00ff88',
  dismissed: '#888',
  escalated: '#ff3355',
}

function SeverityBadge({ severity = 'medium' }) {
  const cfg = SEV_COLORS[severity] || SEV_COLORS.medium
  return (
    <div style={{
      display: 'inline-flex', alignItems: 'center', gap: 5,
      padding: '2px 8px', borderRadius: 2,
      background: cfg.bg, border: `1px solid ${cfg.border}`,
      fontFamily: 'var(--font-mono)', fontSize: 9, letterSpacing: 1,
      color: cfg.text, fontWeight: 700,
      animation: cfg.pulse ? 'sev-pulse 1.6s ease-in-out infinite' : 'none',
    }}>
      {severity === 'critical' && <span style={{ fontSize: 8 }}>⬤ </span>}
      {severity.toUpperCase()}
    </div>
  )
}

const TABLE_HEADERS = ['SEV', 'SCRIP', 'SCHEME TYPE', 'SCORE', 'ACCOUNTS', 'TIME', 'STATUS', '']

function SkeletonRows({ n = 5 }) {
  return (
    <>
      {Array.from({ length: n }).map((_, i) => (
        <div key={i} style={{
          display: 'grid', gridTemplateColumns: '60px 130px 130px 80px 100px 90px 110px 40px',
          padding: '10px 16px', gap: 8, borderBottom: '1px solid var(--border)', alignItems: 'center',
        }}>
          {[40, 100, 90, 50, 70, 60, 70, 20].map((w, j) => (
            <div key={j} className="skeleton" style={{ height: 12, width: `${w}%` }} />
          ))}
        </div>
      ))}
    </>
  )
}

export default function LiveAlerts() {
  const [filters, setFilters] = useState({ scrip: '', status: 'all', min_score: 0, severity: 'all' })
  const [page, setPage]       = useState(1)
  const [newIds, setNewIds]   = useState(new Set())
  const [caseAlert, setCaseAlert] = useState(null)
  const [expandedId, setExpandedId] = useState(null)
  const liveAlerts = useRef([])
  const qc = useQueryClient()
  const PER_PAGE = 10

  const { data, isLoading, isError, refetch } = useQuery(
    ['alerts', filters],
    () => api.getAlerts({
      scrip:     filters.scrip    || undefined,
      status:    filters.status   === 'all' ? undefined : filters.status,
      min_score: filters.min_score > 0       ? filters.min_score : undefined,
      severity:  filters.severity === 'all'  ? undefined : filters.severity,
    }),
    { select: r => r.data }
  )

  useEffect(() => {
    const disconnect = connectLiveAlerts((alert) => {
      liveAlerts.current = [alert, ...liveAlerts.current]
      setNewIds(s => new Set([...s, alert.id]))
      toast.success(`NEW ALERT: ${alert.scrip} — ${Number(alert.impossibility_score).toFixed(1)}/10`, { duration: 5000 })
      refetch()
      setTimeout(() => setNewIds(s => { const n = new Set(s); n.delete(alert.id); return n }), 3000)
    })
    return disconnect
  }, [])

  const alerts      = data?.alerts || (Array.isArray(data) ? data : [])
  const total       = data?.total  || alerts.length
  const open        = alerts.filter(a => a.status === 'open').length
  const avgScore    = alerts.length ? (alerts.reduce((s, a) => s + a.impossibility_score, 0) / alerts.length).toFixed(1) : 0
  const totalAccs   = alerts.reduce((s, a) => s + (a.accounts_involved?.length ?? 0), 0)
  const pending_mit = alerts.filter(a => a.mitigation_status === 'pending').length

  const paged = alerts.slice((page - 1) * PER_PAGE, page * PER_PAGE)
  const pages = Math.ceil(alerts.length / PER_PAGE)

  async function handleMitigate(alert) {
    try {
      await api.mitigateAlert(alert.id, alert.recommended_action || 'monitor_and_log')
      toast.success(`Mitigation applied to ${alert.scrip}`)
      qc.invalidateQueries(['alerts'])
    } catch { toast.error('Mitigation failed') }
  }

  async function handleDismiss(alert) {
    try {
      await api.dismissMitigation(alert.id)
      toast('Mitigation dismissed', { icon: '⊘' })
      qc.invalidateQueries(['alerts'])
    } catch { toast.error('Dismiss failed') }
  }

  async function handleEscalate(alert) {
    try {
      await api.escalateAlert(alert.id)
      toast.success(`${alert.scrip} escalated to SEBI`, { icon: '🔺' })
      qc.invalidateQueries(['alerts'])
    } catch { toast.error('Escalation failed') }
  }

  return (
    <motion.div initial={{ opacity: 0, y: -8 }} animate={{ opacity: 1, y: 0 }} transition={{ duration: 0.2 }}>
      <style>{`
        @keyframes sev-pulse {
          0%,100% { box-shadow: 0 0 0 0 rgba(255,51,85,0.4); }
          50%      { box-shadow: 0 0 0 5px rgba(255,51,85,0); }
        }
      `}</style>

      {/* Metric cards */}
      <div style={{ display: 'grid', gridTemplateColumns: 'repeat(4,1fr)', gap: 16, marginBottom: 24 }}>
        <MetricCard label="Active Alerts"       value={open}        color="var(--accent-red)"   delta={2} deltaLabel=" today" />
        <MetricCard label="Avg Score"           value={avgScore}    color="var(--accent-amber)"  unit="/10" />
        <MetricCard label="Accounts Watched"    value={totalAccs}   color="var(--accent-blue)" />
        <MetricCard label="Pending Mitigation"  value={pending_mit} color="var(--accent-amber)" />
      </div>

      {/* Filter bar */}
      <div style={{
        display: 'flex', gap: 12, marginBottom: 16, alignItems: 'center',
        padding: '12px 16px', background: 'var(--bg-card)', border: '1px solid var(--border)',
        flexWrap: 'wrap',
      }}>
        <input
          placeholder="SEARCH SCRIP..."
          value={filters.scrip}
          onChange={e => { setFilters(f => ({ ...f, scrip: e.target.value })); setPage(1) }}
          style={{ flex: 1, maxWidth: 200 }}
        />
        <select value={filters.status} onChange={e => { setFilters(f => ({ ...f, status: e.target.value })); setPage(1) }} style={{ width: 150 }}>
          <option value="all">ALL STATUS</option>
          <option value="open">OPEN</option>
          <option value="investigating">INVESTIGATING</option>
          <option value="closed">CLOSED</option>
          <option value="false_positive">FALSE POSITIVE</option>
        </select>
        <select value={filters.severity} onChange={e => { setFilters(f => ({ ...f, severity: e.target.value })); setPage(1) }} style={{ width: 130 }}>
          <option value="all">ALL SEVERITY</option>
          <option value="critical">CRITICAL</option>
          <option value="high">HIGH</option>
          <option value="medium">MEDIUM</option>
          <option value="low">LOW</option>
        </select>
        <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
          <span style={{ fontFamily: 'var(--font-mono)', fontSize: 10, color: 'var(--text-secondary)', whiteSpace: 'nowrap' }}>
            MIN SCORE: {filters.min_score.toFixed(1)}
          </span>
          <input type="range" min={0} max={10} step={0.5} value={filters.min_score}
            onChange={e => { setFilters(f => ({ ...f, min_score: parseFloat(e.target.value) })); setPage(1) }}
            style={{ width: 90, accentColor: 'var(--accent-green)' }}
          />
        </div>
        <div style={{ fontFamily: 'var(--font-mono)', fontSize: 10, color: 'var(--text-dim)', marginLeft: 'auto' }}>
          {total} RECORDS
        </div>
      </div>

      {/* Table */}
      <div style={{ background: 'var(--bg-card)', border: '1px solid var(--border)' }}>
        {/* Header */}
        <div style={{
          display: 'grid', gridTemplateColumns: '60px 130px 130px 80px 100px 90px 110px 40px',
          padding: '8px 16px', gap: 8, borderBottom: '1px solid var(--border-bright)', background: 'var(--bg-surface)',
        }}>
          {TABLE_HEADERS.map(h => (
            <div key={h} style={{ fontFamily: 'var(--font-mono)', fontSize: 9, color: 'var(--text-dim)', letterSpacing: 1.5 }}>{h}</div>
          ))}
        </div>

        {isLoading && <SkeletonRows />}
        {isError && (
          <div style={{ padding: 40, textAlign: 'center', color: 'var(--accent-red)', fontFamily: 'var(--font-mono)', fontSize: 12 }}>
            SYSTEM OFFLINE — BACKEND UNAVAILABLE
            <br />
            <button onClick={refetch} style={{ marginTop: 12, background: 'transparent', border: '1px solid var(--accent-red)', color: 'var(--accent-red)', padding: '6px 16px', fontFamily: 'var(--font-mono)', fontSize: 11, cursor: 'pointer' }}>
              RETRY →
            </button>
          </div>
        )}
        {!isLoading && !isError && paged.length === 0 && (
          <div style={{ padding: 60, textAlign: 'center' }}>
            <div style={{ fontFamily: 'var(--font-mono)', color: 'var(--text-secondary)', letterSpacing: 2, fontSize: 11 }}>
              NO ALERTS DETECTED — SYSTEM MONITORING
            </div>
          </div>
        )}

        {!isLoading && paged.map(alert => (
          <div key={alert.id}>
            {/* Row */}
            <div
              onClick={() => setExpandedId(expandedId === alert.id ? null : alert.id)}
              style={{
                display: 'grid', gridTemplateColumns: '60px 130px 130px 80px 100px 90px 110px 40px',
                padding: '10px 16px', gap: 8, borderBottom: '1px solid var(--border)',
                alignItems: 'center', cursor: 'pointer',
                background: newIds.has(alert.id) ? 'rgba(0,255,136,0.05)' : 'transparent',
                transition: 'background 0.2s',
              }}
              onMouseEnter={e => e.currentTarget.style.background = 'var(--bg-surface)'}
              onMouseLeave={e => e.currentTarget.style.background = newIds.has(alert.id) ? 'rgba(0,255,136,0.05)' : 'transparent'}
            >
              <SeverityBadge severity={alert.severity || 'medium'} />
              <div style={{ fontFamily: 'var(--font-mono)', fontSize: 11, fontWeight: 700, color: 'var(--text-primary)' }}>{alert.scrip}</div>
              <div style={{ fontFamily: 'var(--font-mono)', fontSize: 10, color: 'var(--text-secondary)', textTransform: 'uppercase' }}>{(alert.scheme_type || '').replace(/_/g, ' ')}</div>
              <div style={{ fontFamily: 'var(--font-mono)', fontSize: 12, fontWeight: 700, color: alert.impossibility_score >= 9 ? 'var(--accent-red)' : alert.impossibility_score >= 8 ? 'var(--accent-amber)' : 'var(--accent-green)' }}>
                {Number(alert.impossibility_score).toFixed(1)}
              </div>
              <div style={{ fontFamily: 'var(--font-mono)', fontSize: 10, color: 'var(--text-secondary)' }}>{alert.accounts_involved?.length ?? 0} accts</div>
              <div style={{ fontFamily: 'var(--font-mono)', fontSize: 10, color: 'var(--text-dim)' }}>
                {alert.detected_at ? new Date(alert.detected_at).toLocaleTimeString('en-IN', { hour: '2-digit', minute: '2-digit' }) : '—'}
              </div>
              <div style={{
                fontFamily: 'var(--font-mono)', fontSize: 9, padding: '2px 6px', borderRadius: 2,
                background: MIT_STATUS_COLORS[alert.mitigation_status || 'pending'] + '22',
                border: `1px solid ${MIT_STATUS_COLORS[alert.mitigation_status || 'pending']}`,
                color: MIT_STATUS_COLORS[alert.mitigation_status || 'pending'],
                textAlign: 'center', letterSpacing: 0.5,
              }}>
                {(alert.mitigation_status || 'pending').toUpperCase()}
              </div>
              <div style={{ color: 'var(--text-dim)', fontSize: 11, textAlign: 'center' }}>
                {expandedId === alert.id ? '▲' : '▼'}
              </div>
            </div>

            {/* Expanded detail + mitigation actions */}
            <AnimatePresence>
              {expandedId === alert.id && (
                <motion.div
                  initial={{ height: 0, opacity: 0 }} animate={{ height: 'auto', opacity: 1 }}
                  exit={{ height: 0, opacity: 0 }} transition={{ duration: 0.18 }}
                  style={{ overflow: 'hidden', borderBottom: '1px solid var(--border-bright)', background: 'var(--bg-surface)' }}
                >
                  <div style={{ padding: '16px 24px', display: 'grid', gridTemplateColumns: '1fr 1fr 1fr', gap: 24 }}>
                    {/* Scores */}
                    <div>
                      <div style={{ fontFamily: 'var(--font-mono)', fontSize: 9, color: 'var(--text-dim)', letterSpacing: 2, marginBottom: 8 }}>ENGINE SCORES</div>
                      {[
                        ['GNN/TCN', alert.gnn_score],
                        ['DNA', alert.dna_score],
                        ['Cross-Market', alert.cross_market_score],
                        ['Zero-Day', alert.zero_day_score],
                        ['Social Signal', ((alert.social_signal_score || 0) * 10).toFixed(1)],
                        ['Misinformation', ((alert.misinfo_score || 0) * 10).toFixed(1)],
                      ].map(([label, val]) => (
                        <div key={label} style={{ display: 'flex', alignItems: 'center', gap: 8, marginBottom: 4 }}>
                          <div style={{ fontFamily: 'var(--font-mono)', fontSize: 10, color: 'var(--text-secondary)', width: 100, flexShrink: 0 }}>{label}</div>
                          <div style={{ flex: 1, height: 4, background: 'var(--border)', borderRadius: 2 }}>
                            <div style={{ width: `${Math.min(100, (Number(val) / 10) * 100)}%`, height: '100%', background: 'var(--accent-green)', borderRadius: 2 }} />
                          </div>
                          <div style={{ fontFamily: 'var(--font-mono)', fontSize: 10, color: 'var(--text-primary)', width: 30, textAlign: 'right' }}>{Number(val).toFixed(1)}</div>
                        </div>
                      ))}
                    </div>

                    {/* Mitigation info */}
                    <div>
                      <div style={{ fontFamily: 'var(--font-mono)', fontSize: 9, color: 'var(--text-dim)', letterSpacing: 2, marginBottom: 8 }}>MITIGATION</div>
                      <div style={{ marginBottom: 6 }}>
                        <span style={{ fontFamily: 'var(--font-mono)', fontSize: 9, color: 'var(--text-dim)' }}>RECOMMENDED ACTION</span>
                        <div style={{ fontFamily: 'var(--font-mono)', fontSize: 11, color: 'var(--accent-amber)', marginTop: 2 }}>
                          {ACTION_LABELS[alert.recommended_action] || 'MONITOR'}
                        </div>
                      </div>
                      <div style={{ marginBottom: 6 }}>
                        <span style={{ fontFamily: 'var(--font-mono)', fontSize: 9, color: 'var(--text-dim)' }}>MITIGATION STATUS</span>
                        <div style={{
                          display: 'inline-block', marginTop: 2, padding: '1px 8px', borderRadius: 2,
                          fontFamily: 'var(--font-mono)', fontSize: 10,
                          background: MIT_STATUS_COLORS[alert.mitigation_status || 'pending'] + '22',
                          border: `1px solid ${MIT_STATUS_COLORS[alert.mitigation_status || 'pending']}`,
                          color: MIT_STATUS_COLORS[alert.mitigation_status || 'pending'],
                        }}>
                          {(alert.mitigation_status || 'pending').toUpperCase()}
                        </div>
                      </div>
                      {alert.auto_mitigated && (
                        <div style={{ fontFamily: 'var(--font-mono)', fontSize: 9, color: 'var(--accent-green)', marginBottom: 4 }}>AUTO-MITIGATED</div>
                      )}
                      {alert.escalated_to_sebi && (
                        <div style={{ fontFamily: 'var(--font-mono)', fontSize: 9, color: 'var(--accent-red)', marginBottom: 4 }}>ESCALATED TO SEBI</div>
                      )}
                      {alert.mitigation_notes && (
                        <div style={{ fontFamily: 'var(--font-mono)', fontSize: 9, color: 'var(--text-dim)', marginTop: 4, lineHeight: 1.5 }}>
                          {alert.mitigation_notes.length > 120 ? alert.mitigation_notes.slice(0, 120) + '...' : alert.mitigation_notes}
                        </div>
                      )}
                    </div>

                    {/* Action buttons */}
                    <div style={{ display: 'flex', flexDirection: 'column', gap: 8, justifyContent: 'flex-start' }}>
                      <div style={{ fontFamily: 'var(--font-mono)', fontSize: 9, color: 'var(--text-dim)', letterSpacing: 2, marginBottom: 4 }}>ACTIONS</div>
                      <button onClick={e => { e.stopPropagation(); handleMitigate(alert) }} style={{
                        background: 'rgba(0,255,136,0.1)', border: '1px solid var(--accent-green)',
                        color: 'var(--accent-green)', padding: '7px 12px', fontFamily: 'var(--font-mono)',
                        fontSize: 10, cursor: 'pointer', letterSpacing: 1, borderRadius: 2, textAlign: 'left',
                      }}>
                        ✓ APPLY MITIGATION
                      </button>
                      <button onClick={e => { e.stopPropagation(); handleDismiss(alert) }} style={{
                        background: 'transparent', border: '1px solid var(--border-bright)',
                        color: 'var(--text-secondary)', padding: '7px 12px', fontFamily: 'var(--font-mono)',
                        fontSize: 10, cursor: 'pointer', letterSpacing: 1, borderRadius: 2, textAlign: 'left',
                      }}>
                        ⊘ DISMISS
                      </button>
                      <button onClick={e => { e.stopPropagation(); handleEscalate(alert) }} style={{
                        background: 'rgba(255,51,85,0.1)', border: '1px solid var(--accent-red)',
                        color: 'var(--accent-red)', padding: '7px 12px', fontFamily: 'var(--font-mono)',
                        fontSize: 10, cursor: 'pointer', letterSpacing: 1, borderRadius: 2, textAlign: 'left',
                      }}>
                        ▲ ESCALATE TO SEBI
                      </button>
                      <button onClick={e => { e.stopPropagation(); setCaseAlert(alert) }} style={{
                        background: 'rgba(0,136,255,0.1)', border: '1px solid var(--accent-blue)',
                        color: 'var(--accent-blue)', padding: '7px 12px', fontFamily: 'var(--font-mono)',
                        fontSize: 10, cursor: 'pointer', letterSpacing: 1, borderRadius: 2, textAlign: 'left',
                      }}>
                        ⬡ GENERATE CASE PDF
                      </button>
                    </div>
                  </div>
                </motion.div>
              )}
            </AnimatePresence>
          </div>
        ))}
      </div>

      {/* Pagination */}
      {pages > 1 && (
        <div style={{ display: 'flex', gap: 8, justifyContent: 'center', marginTop: 16 }}>
          {Array.from({ length: pages }, (_, i) => i + 1).map(n => (
            <button key={n} onClick={() => setPage(n)} style={{
              width: 32, height: 32,
              background: page === n ? 'var(--accent-green)' : 'var(--bg-card)',
              color: page === n ? '#000' : 'var(--text-secondary)',
              border: '1px solid var(--border)', fontFamily: 'var(--font-mono)', fontSize: 11, cursor: 'pointer',
            }}>{n}</button>
          ))}
        </div>
      )}

      {caseAlert && (
        <CaseModal alert={caseAlert} onClose={() => setCaseAlert(null)} onGenerated={() => setCaseAlert(null)} />
      )}
    </motion.div>
  )
}
