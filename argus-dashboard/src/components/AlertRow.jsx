import { useState } from 'react'
import { AnimatePresence, motion } from 'framer-motion'
import SchemeBadge from './SchemeBadge'
import ScoreBar from './ScoreBar'
import { api } from '../api/client'
import toast from 'react-hot-toast'

function severityColor(score) {
  if (score >= 8.5) return 'var(--accent-red)'
  if (score >= 7.5) return 'var(--accent-amber)'
  return 'var(--accent-green)'
}

function severityLabel(score) {
  if (score >= 8.5) return 'CRITICAL'
  if (score >= 7.5) return 'HIGH'
  if (score >= 6)   return 'MEDIUM'
  return 'LOW'
}

function statusColor(status) {
  if (status === 'open')         return { color:'#00ff88', bg:'rgba(0,255,136,0.1)' }
  if (status === 'under_review') return { color:'#ffb300', bg:'rgba(255,179,0,0.1)' }
  if (status === 'case_filed')   return { color:'#3b82f6', bg:'rgba(59,130,246,0.1)' }
  if (status === 'resolved')     return { color:'#6b6b8a', bg:'rgba(107,107,138,0.1)' }
  if (status === 'false_positive')return { color:'#3a3a55', bg:'rgba(58,58,85,0.1)' }
  return { color:'#6b6b8a', bg:'transparent' }
}

export default function AlertRow({ alert, onGenerateCase, isNew }) {
  const [expanded, setExpanded] = useState(false)
  const score = alert.impossibility_score
  const color = severityColor(score)
  const st    = statusColor(alert.status)

  const fmt = (ts) => {
    const d = new Date(ts)
    return d.toLocaleTimeString('en-IN', { hour12:false, hour:'2-digit', minute:'2-digit', second:'2-digit' })
  }

  const handleAction = async (action) => {
    if (action === 'generate_case') { onGenerateCase(alert); return }
    if (action === 'investigate') {
      await api.updateAlertStatus(alert.id, 'under_review')
      toast.success(`Alert ${alert.scrip} → UNDER REVIEW`)
    }
    if (action === 'close') {
      await api.updateAlertStatus(alert.id, 'resolved')
      toast.success(`Alert ${alert.scrip} → RESOLVED`)
    }
    if (action === 'false_positive') {
      await api.updateAlertStatus(alert.id, 'false_positive')
      toast(`Alert ${alert.scrip} → FALSE POSITIVE`)
    }
  }

  return (
    <div
      className={isNew ? 'flash-new' : ''}
      style={{
        borderLeft: `2px solid ${color}`,
        borderBottom: '1px solid var(--border)',
        transition: 'background 0.15s ease-out',
      }}
    >
      {/* Main row */}
      <div
        onClick={() => setExpanded(e => !e)}
        style={{
          display:'grid',
          gridTemplateColumns:'90px 140px 140px 80px 100px 90px 110px 40px',
          alignItems:'center',
          padding:'10px 16px',
          gap:8,
          cursor:'pointer',
          background: expanded ? 'var(--bg-surface)' : 'transparent',
          transition:'background 0.15s',
        }}
        onMouseEnter={e => !expanded && (e.currentTarget.style.background='var(--bg-card-hover)')}
        onMouseLeave={e => !expanded && (e.currentTarget.style.background='transparent')}
      >
        {/* Severity */}
        <span style={{
          fontFamily:'var(--font-mono)', fontSize:9, fontWeight:600,
          letterSpacing:1, color,
        }}>
          [{severityLabel(score)}]
        </span>

        {/* Scrip */}
        <span style={{ fontFamily:'var(--font-mono)', fontSize:12, fontWeight:500, color:'var(--text-primary)' }}>
          {alert.scrip}
        </span>

        {/* Scheme */}
        <SchemeBadge type={alert.scheme_type} />

        {/* Score */}
        <span style={{
          fontFamily:'var(--font-mono)', fontSize:13, fontWeight:600,
          color, textAlign:'center',
        }}>
          {score.toFixed(1)}/10
        </span>

        {/* Accounts */}
        <span style={{ fontFamily:'var(--font-mono)', fontSize:11, color:'var(--text-secondary)' }}>
          {alert.accounts_involved?.length ?? 0} accs
        </span>

        {/* Time */}
        <span style={{ fontFamily:'var(--font-mono)', fontSize:11, color:'var(--text-dim)' }}>
          {fmt(alert.detected_at)}
        </span>

        {/* Status */}
        <span style={{
          fontFamily:'var(--font-mono)', fontSize:9, letterSpacing:1,
          color:st.color, background:st.bg, padding:'2px 6px',
          border:`1px solid ${st.color}40`,
        }}>
          {alert.status.toUpperCase().replace('_',' ')}
        </span>

        {/* Expand toggle */}
        <span style={{
          color:'var(--text-dim)', fontSize:12, textAlign:'center',
          transform: expanded ? 'rotate(90deg)' : 'none',
          transition:'transform 0.15s',
        }}>›</span>
      </div>

      {/* Expanded detail */}
      <AnimatePresence>
        {expanded && (
          <motion.div
            initial={{ height:0, opacity:0 }}
            animate={{ height:'auto', opacity:1 }}
            exit={{ height:0, opacity:0 }}
            transition={{ duration:0.2 }}
            style={{ overflow:'hidden', background:'var(--bg-surface)' }}
          >
            <div style={{ padding:'16px 24px', borderTop:'1px solid var(--border)' }}>
              <div style={{ display:'grid', gridTemplateColumns:'1fr 1fr', gap:24 }}>
                {/* Score breakdown */}
                <div>
                  <div style={{ fontSize:9, color:'var(--text-dim)', letterSpacing:2, marginBottom:10 }}>
                    SCORE BREAKDOWN
                  </div>
                  <ScoreBar label="GNN COORDINATION" score={alert.gnn_score ?? 0} weight={35} />
                  <ScoreBar label="DNA ANOMALY" score={alert.dna_score ?? 0} weight={25} />
                  <ScoreBar label="CROSS-MARKET" score={alert.cross_market_score ?? 0} weight={15} />
                  <ScoreBar label="ZERO-DAY" score={alert.zero_day_score ?? 0} weight={25} />
                </div>

                {/* Accounts + actions */}
                <div>
                  <div style={{ fontSize:9, color:'var(--text-dim)', letterSpacing:2, marginBottom:10 }}>
                    ACCOUNTS INVOLVED ({alert.accounts_involved?.length})
                  </div>
                  <div style={{ display:'flex', flexWrap:'wrap', gap:4, marginBottom:16 }}>
                    {(alert.accounts_involved || []).slice(0,12).map(acc => (
                      <span key={acc} style={{
                        fontFamily:'var(--font-mono)', fontSize:9,
                        color:'var(--accent-red)', background:'rgba(255,51,85,0.08)',
                        border:'1px solid rgba(255,51,85,0.2)',
                        padding:'2px 6px',
                      }}>{acc}</span>
                    ))}
                    {(alert.accounts_involved?.length ?? 0) > 12 && (
                      <span style={{ fontFamily:'var(--font-mono)', fontSize:9, color:'var(--text-dim)', padding:'2px 4px' }}>
                        +{alert.accounts_involved.length - 12} more
                      </span>
                    )}
                  </div>

                  <div style={{ display:'flex', gap:8, flexWrap:'wrap' }}>
                    {[
                      { label:'INVESTIGATE', action:'investigate', color:'var(--accent-amber)' },
                      { label:'GENERATE CASE', action:'generate_case', color:'var(--accent-green)' },
                      { label:'CLOSE', action:'close', color:'var(--text-secondary)' },
                      { label:'FALSE POSITIVE', action:'false_positive', color:'var(--text-dim)' },
                    ].map(({ label, action, color }) => (
                      <button
                        key={action}
                        onClick={(e)=>{ e.stopPropagation(); handleAction(action) }}
                        style={{
                          fontFamily:'var(--font-mono)', fontSize:9,
                          color, background:'transparent',
                          border:`1px solid ${color}60`,
                          padding:'4px 10px',
                          letterSpacing:1,
                        }}
                        onMouseEnter={e => e.currentTarget.style.background = `${color}15`}
                        onMouseLeave={e => e.currentTarget.style.background = 'transparent'}
                      >
                        {label}
                      </button>
                    ))}
                  </div>
                </div>
              </div>
            </div>
          </motion.div>
        )}
      </AnimatePresence>
    </div>
  )
}
