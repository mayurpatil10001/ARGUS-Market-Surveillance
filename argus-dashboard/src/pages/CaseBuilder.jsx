import { useState } from 'react'
import { useQuery } from 'react-query'
import { motion } from 'framer-motion'
import { api } from '../api/client'
import SchemeBadge from '../components/SchemeBadge'
import ScoreBar from '../components/ScoreBar'
import CaseModal from '../components/CaseModal'

function severityColor(score) {
  if (score >= 8.5) return 'var(--accent-red)'
  if (score >= 7.5) return 'var(--accent-amber)'
  return 'var(--accent-green)'
}

export default function CaseBuilder() {
  const [selected, setSelected] = useState(null)
  const [modal, setModal]       = useState(false)
  const [caseResult, setCaseResult] = useState(null)

  const { data, isLoading } = useQuery(
    'open_alerts_case',
    () => api.getAlerts({ status:'open' }),
    { select: r => r.data }
  )
  const alerts = (data?.alerts || []).sort((a,b) => b.impossibility_score - a.impossibility_score)

  const handleGenerated = (result) => {
    setCaseResult(result)
    setModal(false)
  }

  return (
    <motion.div initial={{ opacity:0, y:-8 }} animate={{ opacity:1, y:0 }} transition={{ duration:0.2 }}>
      <div style={{ display:'grid', gridTemplateColumns:'400px 1fr', gap:20, minHeight:600 }}>
        {/* Alert selector */}
        <div style={{ background:'var(--bg-card)', border:'1px solid var(--border)' }}>
          <div style={{
            padding:'14px 16px',
            borderBottom:'1px solid var(--border)',
            fontFamily:'var(--font-mono)', fontSize:10, color:'var(--text-dim)', letterSpacing:2,
          }}>
            SELECT ALERT TO FILE
          </div>
          <div style={{ overflowY:'auto', maxHeight:700 }}>
            {isLoading && Array.from({length:5}).map((_,i) => (
              <div key={i} className="skeleton" style={{ height:60, margin:8 }} />
            ))}
            {alerts.map(alert => {
              const color = severityColor(alert.impossibility_score)
              const isSelected = selected?.id === alert.id
              return (
                <div
                  key={alert.id}
                  onClick={() => { setSelected(alert); setCaseResult(null) }}
                  style={{
                    padding:'12px 16px',
                    borderBottom:'1px solid var(--border)',
                    borderLeft: `2px solid ${isSelected ? color : 'transparent'}`,
                    cursor:'pointer',
                    background: isSelected ? 'var(--bg-surface)' : 'transparent',
                    transition:'all 0.15s',
                  }}
                  onMouseEnter={e => !isSelected && (e.currentTarget.style.background='var(--bg-card-hover)')}
                  onMouseLeave={e => !isSelected && (e.currentTarget.style.background='transparent')}
                >
                  <div style={{ display:'flex', alignItems:'center', gap:8, marginBottom:5 }}>
                    <span style={{
                      fontFamily:'var(--font-mono)', fontWeight:600, fontSize:13,
                      color, minWidth:48,
                    }}>
                      {alert.impossibility_score.toFixed(1)}
                    </span>
                    <span style={{ fontFamily:'var(--font-mono)', fontWeight:600, fontSize:13, color:'var(--text-primary)' }}>
                      {alert.scrip}
                    </span>
                    <SchemeBadge type={alert.scheme_type} />
                  </div>
                  <div style={{ display:'flex', gap:12, alignItems:'center' }}>
                    <span style={{ fontFamily:'var(--font-mono)', fontSize:10, color:'var(--text-dim)' }}>
                      {new Date(alert.detected_at).toLocaleDateString('en-IN')}
                    </span>
                    <span style={{ fontFamily:'var(--font-mono)', fontSize:10, color:'var(--text-secondary)' }}>
                      {alert.accounts_involved?.length ?? 0} accounts
                    </span>
                    {isSelected && (
                      <span style={{
                        marginLeft:'auto', fontFamily:'var(--font-mono)', fontSize:9,
                        color:'var(--accent-green)', letterSpacing:1,
                      }}>
                        SELECTED
                      </span>
                    )}
                  </div>
                </div>
              )
            })}
          </div>
        </div>

        {/* Right panel */}
        <div>
          {!selected ? (
            <div style={{
              height:'100%', display:'flex', alignItems:'center', justifyContent:'center',
              background:'var(--bg-card)', border:'1px solid var(--border)',
              fontFamily:'var(--font-mono)', color:'var(--text-dim)', fontSize:12, letterSpacing:2,
            }}>
              ← SELECT AN ALERT TO BEGIN
            </div>
          ) : (
            <div style={{ background:'var(--bg-card)', border:'1px solid var(--border)', padding:24 }}>
              {/* Alert summary */}
              <div style={{ marginBottom:20 }}>
                <div style={{ display:'flex', alignItems:'center', gap:12, marginBottom:12 }}>
                  <div style={{ fontFamily:'var(--font-display)', fontWeight:700, fontSize:20, color:'var(--text-primary)', letterSpacing:2 }}>
                    {selected.scrip}
                  </div>
                  <SchemeBadge type={selected.scheme_type} />
                  <div style={{ marginLeft:'auto', fontFamily:'var(--font-mono)', fontWeight:600, fontSize:24,
                    color:severityColor(selected.impossibility_score) }}>
                    {selected.impossibility_score.toFixed(1)}/10
                  </div>
                </div>
                <div style={{ marginBottom:16 }}>
                  <ScoreBar label="GNN COORDINATION" score={selected.gnn_score ?? 0} weight={35} />
                  <ScoreBar label="DNA ANOMALY"      score={selected.dna_score ?? 0} weight={25} />
                  <ScoreBar label="CROSS-MARKET"     score={selected.cross_market_score ?? 0} weight={15} />
                  <ScoreBar label="ZERO-DAY"         score={selected.zero_day_score ?? 0} weight={25} />
                </div>
              </div>

              {/* Case result */}
              {caseResult ? (
                <div style={{ padding:24, textAlign:'center', border:'1px solid rgba(0,255,136,0.3)', background:'rgba(0,255,136,0.03)' }}>
                  <div style={{ fontSize:10, fontFamily:'var(--font-mono)', color:'var(--text-secondary)', letterSpacing:2, marginBottom:8 }}>
                    CASE NUMBER ISSUED
                  </div>
                  <div style={{
                    fontFamily:'var(--font-display)', fontWeight:700, fontSize:22,
                    color:'var(--accent-green)', letterSpacing:4, marginBottom:16,
                  }}>
                    {caseResult.case_number}
                  </div>
                  <a
                    href={caseResult.pdf_url}
                    target="_blank"
                    rel="noreferrer"
                    style={{
                      display:'inline-block', padding:'10px 32px',
                      background:'var(--accent-green)', color:'#000',
                      fontFamily:'var(--font-display)', fontWeight:700, fontSize:13,
                    }}
                  >
                    DOWNLOAD PDF ({caseResult.file_size_kb ?? 284} KB) →
                  </a>
                </div>
              ) : (
                <button
                  onClick={() => setModal(true)}
                  style={{
                    width:'100%', padding:16,
                    background:'var(--accent-green)', color:'#000',
                    fontFamily:'var(--font-display)', fontWeight:700, fontSize:15,
                    border:'none', cursor:'pointer', letterSpacing:1,
                    transition:'all 0.15s',
                  }}
                  onMouseEnter={e => e.currentTarget.style.background='#00cc6a'}
                  onMouseLeave={e => e.currentTarget.style.background='var(--accent-green)'}
                >
                  GENERATE SEBI CASE FILE →
                </button>
              )}
            </div>
          )}
        </div>
      </div>

      {modal && selected && (
        <CaseModal
          alert={selected}
          onClose={() => setModal(false)}
          onGenerated={handleGenerated}
        />
      )}
    </motion.div>
  )
}
