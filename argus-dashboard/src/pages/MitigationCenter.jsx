import { useState } from 'react'
import { useQuery, useQueryClient } from 'react-query'
import { motion } from 'framer-motion'
import toast from 'react-hot-toast'
import { PieChart, Pie, Cell, Tooltip, ResponsiveContainer, Legend } from 'recharts'
import { api } from '../api/client'
import MetricCard from '../components/MetricCard'

const SEV_COLORS = {
  critical: '#ff3355',
  high:     '#ff8c00',
  medium:   '#ffb300',
  low:      '#4caf50',
}

const MIT_STATUS_COLORS = {
  pending:   '#ffb300',
  applied:   '#00ff88',
  dismissed: '#666',
  escalated: '#ff3355',
}

const ACTION_LABELS = {
  freeze_accounts_and_escalate_sebi:        'FREEZE + ESCALATE',
  freeze_accounts_pending_review:           'FREEZE ACCOUNTS',
  flag_accounts_for_investigation:          'FLAG INVESTIGATE',
  block_social_signals_and_alert_compliance:'BLOCK SOCIAL',
  flag_content_and_notify_exchange:         'FLAG CONTENT',
  block_domain_and_alert_users:             'BLOCK DOMAIN',
  isolate_entity_and_escalate:              'ISOLATE + ESCALATE',
  flag_entity_for_review:                   'FLAG ENTITY',
  monitor_and_log:                          'MONITOR',
}

function SeverityBadge({ severity = 'medium' }) {
  const color = SEV_COLORS[severity] || '#888'
  return (
    <span style={{
      display: 'inline-block', padding: '2px 7px', borderRadius: 2,
      background: color + '22', border: `1px solid ${color}`,
      fontFamily: 'var(--font-mono)', fontSize: 9, letterSpacing: 1,
      color, fontWeight: 700,
    }}>
      {severity.toUpperCase()}
    </span>
  )
}

function ActionBtn({ children, color = 'var(--accent-green)', onClick }) {
  return (
    <button onClick={onClick} style={{
      background: color + '18', border: `1px solid ${color}`,
      color, padding: '5px 10px', fontFamily: 'var(--font-mono)',
      fontSize: 9, cursor: 'pointer', letterSpacing: 0.8,
      borderRadius: 2, whiteSpace: 'nowrap',
    }}>
      {children}
    </button>
  )
}

export default function MitigationCenter() {
  const [sevFilter, setSevFilter] = useState('all')
  const [simScenario, setSimScenario] = useState('all')
  const [simRunning, setSimRunning] = useState(false)
  const [simResult, setSimResult] = useState(null)
  const [simModalOpen, setSimModalOpen] = useState(false)
  const [simError, setSimError] = useState(null)
  const qc = useQueryClient()

  const { data: summary = {} } = useQuery(
    'mitigation-summary',
    () => api.getMitigationSummary().then(r => r.data),
    { refetchInterval: 30000 }
  )

  const { data: pending = [], isLoading } = useQuery(
    ['mitigation-pending', sevFilter],
    () => api.getMitigationPending(sevFilter).then(r => r.data),
    { refetchInterval: 30000 }
  )

  async function handleApply(alert) {
    try {
      await api.mitigateAlert(alert.id, alert.recommended_action || 'monitor_and_log', 'analyst', 'Applied from Mitigation Center')
      toast.success(`Mitigation applied — ${alert.scrip}`)
      qc.invalidateQueries('mitigation-pending')
      qc.invalidateQueries('mitigation-summary')
    } catch { toast.error('Apply failed') }
  }

  async function handleDismiss(alert) {
    try {
      await api.dismissMitigation(alert.id, 'analyst', 'Dismissed from Mitigation Center')
      toast('Dismissed', { icon: '⊘' })
      qc.invalidateQueries('mitigation-pending')
      qc.invalidateQueries('mitigation-summary')
    } catch { toast.error('Dismiss failed') }
  }

  async function handleEscalate(alert) {
    try {
      await api.escalateAlert(alert.id, 'analyst')
      toast.success(`${alert.scrip} escalated to SEBI`, { icon: '🔺' })
      qc.invalidateQueries('mitigation-pending')
      qc.invalidateQueries('mitigation-summary')
    } catch { toast.error('Escalation failed') }
  }

  // Pie chart data for severity
  const pieData = Object.entries(summary.by_severity || {}).map(([name, value]) => ({
    name: name.toUpperCase(), value, color: SEV_COLORS[name] || '#888'
  })).filter(d => d.value > 0)

  return (
    <motion.div initial={{ opacity: 0, y: -8 }} animate={{ opacity: 1, y: 0 }} transition={{ duration: 0.2 }}>
      {/* Page header */}
      <div style={{ marginBottom: 24 }}>
        <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', flexWrap: 'wrap', gap: 12 }}>
          <div>
            <div style={{ fontFamily: 'var(--font-display)', fontWeight: 800, fontSize: 20, color: 'var(--text-primary)', letterSpacing: 2 }}>
              MITIGATION CENTER
            </div>
            <div style={{ fontFamily: 'var(--font-mono)', fontSize: 10, color: 'var(--text-dim)', marginTop: 4 }}>
              Real-time alert triage — apply, dismiss, or escalate recommended actions
            </div>
          </div>
          {/* Simulation controls */}
          <div style={{ display: 'flex', alignItems: 'center', gap: 10 }}>
            <select
              value={simScenario}
              onChange={e => setSimScenario(e.target.value)}
              disabled={simRunning}
              style={{
                background: 'var(--bg-surface)', border: '1px solid var(--border-bright)',
                color: 'var(--text-secondary)', fontFamily: 'var(--font-mono)', fontSize: 10,
                padding: '6px 10px', borderRadius: 4, cursor: 'pointer',
              }}
            >
              <option value="all">All Scenarios</option>
              <option value="pump_dump">Pump &amp; Dump</option>
              <option value="spoofing">Spoofing</option>
              <option value="circular_trading">Circular Trading</option>
              <option value="social_manipulation">Social Manipulation</option>
              <option value="phishing_campaign">Phishing Campaign</option>
            </select>
            <button
              onClick={async () => {
                setSimRunning(true); setSimError(null); setSimResult(null)
                try {
                  const token = localStorage.getItem('argus_token')
                  const resp = await fetch('/alerts/simulate', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json', Authorization: `Bearer ${token}` },
                    body: JSON.stringify({ scenario: simScenario }),
                  })
                  if (!resp.ok) throw new Error(`${resp.status} ${resp.statusText}`)
                  const data = await resp.json()
                  setSimResult(data)
                  setSimModalOpen(true)
                  qc.invalidateQueries('mitigation-summary')
                  qc.invalidateQueries('mitigation-pending')
                } catch (e) {
                  setSimError(e.message)
                } finally {
                  setSimRunning(false)
                }
              }}
              disabled={simRunning}
              style={{
                display: 'flex', alignItems: 'center', gap: 8,
                padding: '7px 16px',
                border: '1px solid var(--accent-green)',
                background: simRunning ? 'rgba(34,211,238,0.05)' : 'rgba(34,211,238,0.1)',
                color: 'var(--accent-green)',
                fontFamily: 'var(--font-mono)', fontSize: 11, fontWeight: 700, letterSpacing: 1.5,
                borderRadius: 6, cursor: simRunning ? 'wait' : 'pointer',
                transition: 'all 0.15s',
              }}
            >
              {simRunning
                ? <><span style={{ display: 'inline-block', width: 12, height: 12, border: '2px solid var(--accent-green)', borderTopColor: 'transparent', borderRadius: '50%', animation: 'spin 0.8s linear infinite' }} /> SIMULATION RUNNING...</>
                : '▶ RUN SIMULATION'
              }
            </button>
          </div>
        </div>
        {simError && (
          <div style={{ marginTop: 8, padding: '6px 12px', background: 'rgba(239,68,68,0.1)', border: '1px solid #ef444455', borderRadius: 4, color: '#ef4444', fontFamily: 'var(--font-mono)', fontSize: 10 }}>
            Simulation error: {simError}
          </div>
        )}
      </div>

      {/* Simulation Results Modal */}
      {simModalOpen && simResult && (
        <div style={{
          position: 'fixed', inset: 0, background: 'rgba(0,0,0,0.85)',
          display: 'flex', alignItems: 'center', justifyContent: 'center',
          zIndex: 9999, padding: 24,
        }}>
          <div style={{
            background: 'var(--bg-card)', border: '1px solid var(--border-bright)',
            borderRadius: 10, width: '100%', maxWidth: 860,
            maxHeight: '90vh', overflow: 'auto', padding: 28,
          }}>
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 20 }}>
              <div style={{ fontFamily: 'var(--font-display)', fontSize: 18, fontWeight: 800, color: 'var(--accent-green)', letterSpacing: 3 }}>
                SIMULATION RESULTS
              </div>
              <button onClick={() => setSimModalOpen(false)} style={{ background: 'transparent', border: 'none', color: 'var(--text-dim)', cursor: 'pointer', fontSize: 18 }}>✕</button>
            </div>

            {/* Summary cards */}
            <div style={{ display: 'grid', gridTemplateColumns: 'repeat(4,1fr)', gap: 12, marginBottom: 20 }}>
              {[
                ['SCENARIOS RUN', simResult.summary?.total_scenarios, 'var(--accent-green)'],
                ['PASSED', simResult.summary?.passed, '#22c55e'],
                ['ALERTS CREATED', simResult.summary?.alerts_created, 'var(--accent-amber)'],
                ['AVG DETECT TIME', `${simResult.summary?.avg_detection_time_ms?.toFixed(0)}ms`, 'var(--accent-blue)'],
              ].map(([label, value, color]) => (
                <div key={label} style={{ background: 'rgba(255,255,255,0.04)', border: '1px solid var(--border)', borderRadius: 6, padding: '12px 14px' }}>
                  <div style={{ fontSize: 8, color: 'var(--text-dim)', fontFamily: 'var(--font-mono)', letterSpacing: 2, marginBottom: 4 }}>{label}</div>
                  <div style={{ fontSize: 20, fontWeight: 800, color, fontFamily: 'var(--font-mono)' }}>{value}</div>
                </div>
              ))}
            </div>

            {/* Per-scenario table */}
            <div style={{ border: '1px solid var(--border)', borderRadius: 6, overflow: 'hidden' }}>
              <div style={{ display: 'grid', gridTemplateColumns: '180px 70px 90px 100px 1fr 110px', padding: '8px 14px', background: 'var(--bg-surface)', gap: 10, borderBottom: '1px solid var(--border)' }}>
                {['SCENARIO', 'STATUS', 'THREAT', 'SEVERITY', 'RECOMMENDED ACTION', 'DETECT TIME'].map(h => (
                  <div key={h} style={{ fontFamily: 'var(--font-mono)', fontSize: 9, color: 'var(--text-dim)', letterSpacing: 1.5 }}>{h}</div>
                ))}
              </div>
              {Object.entries(simResult.results || {}).map(([name, r], i) => (
                <div key={name} style={{
                  display: 'grid', gridTemplateColumns: '180px 70px 90px 100px 1fr 110px',
                  padding: '10px 14px', gap: 10, alignItems: 'center',
                  borderBottom: '1px solid var(--border)',
                  background: i % 2 === 0 ? 'transparent' : 'rgba(255,255,255,0.01)'
                }}>
                  <div style={{ fontFamily: 'var(--font-mono)', fontSize: 11, color: 'var(--text-primary)', fontWeight: 600 }}>
                    {name.replace(/_/g, ' ').toUpperCase()}
                  </div>
                  <div>
                    <span style={{
                      padding: '2px 8px', borderRadius: 3, fontSize: 9, fontWeight: 700,
                      fontFamily: 'var(--font-mono)', letterSpacing: 1.5,
                      background: r.status === 'pass' ? 'rgba(34,197,94,0.15)' : 'rgba(239,68,68,0.15)',
                      border: `1px solid ${r.status === 'pass' ? '#22c55e' : '#ef4444'}`,
                      color: r.status === 'pass' ? '#22c55e' : '#ef4444',
                    }}>{r.status?.toUpperCase()}</span>
                  </div>
                  <div style={{ fontFamily: 'var(--font-mono)', fontSize: 12, fontWeight: 700, color: r.threat_score >= 0.75 ? '#ef4444' : r.threat_score >= 0.5 ? '#f97316' : '#22c55e' }}>
                    {((r.threat_score || 0) * 100).toFixed(0)}%
                  </div>
                  <div style={{ fontFamily: 'var(--font-mono)', fontSize: 10, color: 'var(--text-secondary)', textTransform: 'uppercase' }}>
                    {r.severity}
                  </div>
                  <div style={{ fontFamily: 'var(--font-mono)', fontSize: 9, color: 'var(--accent-amber)', letterSpacing: 0.5 }}>
                    {(r.recommended_action || '').replace(/_/g, ' ')}
                  </div>
                  <div style={{ fontFamily: 'var(--font-mono)', fontSize: 10, color: 'var(--text-dim)' }}>
                    {r.detection_time_ms?.toFixed(0)}ms
                  </div>
                </div>
              ))}
            </div>

            <div style={{ marginTop: 20, display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
              <div style={{ fontFamily: 'var(--font-mono)', fontSize: 9, color: 'var(--text-dim)' }}>
                sim_id: {simResult.simulation_id} · duration: {simResult.total_duration_ms?.toFixed(0)}ms · all data: synthetic
              </div>
              <button
                onClick={() => setSimModalOpen(false)}
                style={{
                  padding: '7px 20px',
                  background: 'transparent',
                  border: '1px solid var(--border)',
                  color: 'var(--text-secondary)',
                  fontFamily: 'var(--font-mono)', fontSize: 11, letterSpacing: 2,
                  borderRadius: 4, cursor: 'pointer',
                }}
              >
                CLOSE
              </button>
            </div>
          </div>
        </div>
      )}

      {/* Summary cards */}
      <div style={{ display: 'grid', gridTemplateColumns: 'repeat(4,1fr)', gap: 16, marginBottom: 24 }}>
        <MetricCard label="Pending Mitigation" value={summary.pending_mitigation ?? 0} color="var(--accent-amber)" />
        <MetricCard label="Applied"            value={summary.applied ?? 0}            color="var(--accent-green)" />
        <MetricCard label="Escalated to SEBI"  value={summary.escalated_to_sebi ?? 0}  color="var(--accent-red)" />
        <MetricCard label="Auto-Mitigated"     value={summary.auto_mitigated ?? 0}      color="var(--accent-blue)" />
      </div>

      {/* Charts row */}
      <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 16, marginBottom: 24 }}>
        {/* Severity donut */}
        <div style={{ background: 'var(--bg-card)', border: '1px solid var(--border)', padding: 20 }}>
          <div style={{ fontFamily: 'var(--font-mono)', fontSize: 9, color: 'var(--text-dim)', letterSpacing: 2, marginBottom: 12 }}>SEVERITY BREAKDOWN</div>
          {pieData.length > 0 ? (
            <ResponsiveContainer width="100%" height={200}>
              <PieChart>
                <Pie data={pieData} cx="50%" cy="50%" innerRadius={55} outerRadius={80} paddingAngle={3} dataKey="value">
                  {pieData.map((entry, i) => <Cell key={i} fill={entry.color} />)}
                </Pie>
                <Tooltip
                  contentStyle={{ background: 'var(--bg-surface)', border: '1px solid var(--border)', fontFamily: 'var(--font-mono)', fontSize: 11 }}
                  formatter={(value, name) => [value, name]}
                />
                <Legend wrapperStyle={{ fontFamily: 'var(--font-mono)', fontSize: 10 }} />
              </PieChart>
            </ResponsiveContainer>
          ) : (
            <div style={{ height: 200, display: 'flex', alignItems: 'center', justifyContent: 'center', color: 'var(--text-dim)', fontFamily: 'var(--font-mono)', fontSize: 11 }}>
              No data
            </div>
          )}
        </div>

        {/* Action breakdown */}
        <div style={{ background: 'var(--bg-card)', border: '1px solid var(--border)', padding: 20 }}>
          <div style={{ fontFamily: 'var(--font-mono)', fontSize: 9, color: 'var(--text-dim)', letterSpacing: 2, marginBottom: 12 }}>RECOMMENDED ACTIONS</div>
          {Object.entries(summary.by_action || {}).map(([action, count]) => (
            <div key={action} style={{ display: 'flex', alignItems: 'center', gap: 10, marginBottom: 8 }}>
              <div style={{ fontFamily: 'var(--font-mono)', fontSize: 9, color: 'var(--text-secondary)', width: 180, flexShrink: 0 }}>
                {ACTION_LABELS[action] || action.replace(/_/g, ' ').toUpperCase()}
              </div>
              <div style={{ flex: 1, height: 4, background: 'var(--border)', borderRadius: 2 }}>
                <div style={{
                  width: `${Math.min(100, (count / (summary.total_alerts || 1)) * 100)}%`,
                  height: '100%', background: 'var(--accent-amber)', borderRadius: 2,
                }} />
              </div>
              <div style={{ fontFamily: 'var(--font-mono)', fontSize: 10, color: 'var(--text-primary)', width: 20, textAlign: 'right' }}>{count}</div>
            </div>
          ))}
          {/* Status row */}
          <div style={{ height: 1, background: 'var(--border)', margin: '12px 0' }} />
          <div style={{ display: 'flex', gap: 16 }}>
            {[['DISMISSED', summary.dismissed, '#666'], ['ESCALATED', summary.escalated, '#ff3355']].map(([label, val, color]) => (
              <div key={label} style={{ fontFamily: 'var(--font-mono)', fontSize: 9 }}>
                <div style={{ color: 'var(--text-dim)' }}>{label}</div>
                <div style={{ color, fontSize: 18, fontWeight: 700 }}>{val ?? 0}</div>
              </div>
            ))}
          </div>
        </div>
      </div>

      {/* Pending table */}
      <div style={{ background: 'var(--bg-card)', border: '1px solid var(--border)' }}>
        {/* Table header bar */}
        <div style={{
          display: 'flex', alignItems: 'center', justifyContent: 'space-between',
          padding: '10px 16px', borderBottom: '1px solid var(--border-bright)', background: 'var(--bg-surface)',
        }}>
          <div style={{ fontFamily: 'var(--font-mono)', fontSize: 9, color: 'var(--text-dim)', letterSpacing: 2 }}>
            PENDING MITIGATION — {pending.length} ALERTS
          </div>
          <select value={sevFilter} onChange={e => setSevFilter(e.target.value)} style={{ fontSize: 10 }}>
            <option value="all">ALL SEVERITY</option>
            <option value="critical">CRITICAL</option>
            <option value="high">HIGH</option>
            <option value="medium">MEDIUM</option>
            <option value="low">LOW</option>
          </select>
        </div>

        {/* Column headers */}
        <div style={{
          display: 'grid', gridTemplateColumns: '70px 130px 130px 80px 160px 110px 270px',
          padding: '7px 16px', gap: 8, borderBottom: '1px solid var(--border)',
        }}>
          {['SEV', 'SCRIP', 'SCHEME', 'SCORE', 'RECOMMENDED ACTION', 'DETECTED', 'ACTIONS'].map(h => (
            <div key={h} style={{ fontFamily: 'var(--font-mono)', fontSize: 9, color: 'var(--text-dim)', letterSpacing: 1.5 }}>{h}</div>
          ))}
        </div>

        {isLoading && (
          <div style={{ padding: 32, textAlign: 'center', color: 'var(--text-dim)', fontFamily: 'var(--font-mono)', fontSize: 11 }}>
            LOADING...
          </div>
        )}

        {!isLoading && pending.length === 0 && (
          <div style={{ padding: 48, textAlign: 'center' }}>
            <div style={{ fontFamily: 'var(--font-mono)', fontSize: 11, color: 'var(--accent-green)', letterSpacing: 2 }}>
              ALL CLEAR — NO PENDING MITIGATIONS
            </div>
          </div>
        )}

        {!isLoading && pending.map((alert, idx) => (
          <div key={alert.id} style={{
            display: 'grid', gridTemplateColumns: '70px 130px 130px 80px 160px 110px 270px',
            padding: '10px 16px', gap: 8, borderBottom: '1px solid var(--border)',
            alignItems: 'center',
            background: idx % 2 === 0 ? 'transparent' : 'rgba(255,255,255,0.01)',
          }}>
            <SeverityBadge severity={alert.severity || 'medium'} />
            <div style={{ fontFamily: 'var(--font-mono)', fontSize: 11, fontWeight: 700, color: 'var(--text-primary)' }}>
              {alert.scrip}
            </div>
            <div style={{ fontFamily: 'var(--font-mono)', fontSize: 9, color: 'var(--text-secondary)', textTransform: 'uppercase' }}>
              {(alert.scheme_type || '').replace(/_/g, ' ')}
            </div>
            <div style={{
              fontFamily: 'var(--font-mono)', fontSize: 12, fontWeight: 700,
              color: alert.impossibility_score >= 9 ? 'var(--accent-red)' : alert.impossibility_score >= 8 ? 'var(--accent-amber)' : 'var(--accent-green)',
            }}>
              {Number(alert.impossibility_score).toFixed(1)}
            </div>
            <div style={{ fontFamily: 'var(--font-mono)', fontSize: 9, color: 'var(--accent-amber)', letterSpacing: 0.5 }}>
              {ACTION_LABELS[alert.recommended_action] || 'MONITOR'}
            </div>
            <div style={{ fontFamily: 'var(--font-mono)', fontSize: 10, color: 'var(--text-dim)' }}>
              {alert.detected_at ? new Date(alert.detected_at).toLocaleString('en-IN', { month: 'short', day: 'numeric', hour: '2-digit', minute: '2-digit' }) : '—'}
            </div>
            <div style={{ display: 'flex', gap: 6 }}>
              <ActionBtn color="var(--accent-green)" onClick={() => handleApply(alert)}>✓ APPLY</ActionBtn>
              <ActionBtn color="var(--text-secondary)" onClick={() => handleDismiss(alert)}>⊘ DISMISS</ActionBtn>
              <ActionBtn color="var(--accent-red)" onClick={() => handleEscalate(alert)}>▲ SEBI</ActionBtn>
            </div>
          </div>
        ))}
      </div>
    </motion.div>
  )
}
