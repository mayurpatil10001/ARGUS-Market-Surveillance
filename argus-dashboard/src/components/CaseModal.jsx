import { useState } from 'react'
import { motion, AnimatePresence } from 'framer-motion'
import { api } from '../api/client'
import ScoreBar from './ScoreBar'
import SchemeBadge from './SchemeBadge'
import toast from 'react-hot-toast'

export default function CaseModal({ alert, onClose, onGenerated }) {
  const [form, setForm] = useState({
    entity_names: (alert.accounts_involved || []).slice(0,3).join(', '),
    estimated_gain: alert.estimated_gain ?? '',
    from_date: new Date(Date.now()-7*86400000).toISOString().split('T')[0],
    to_date:   new Date().toISOString().split('T')[0],
    notes: '',
  })
  const [loading, setLoading] = useState(false)
  const [result, setResult] = useState(null)

  const handleGenerate = async () => {
    setLoading(true)
    try {
      const r = await api.generateCase(alert.id, {
        entity_names: form.entity_names.split(',').map(s=>s.trim()),
        estimated_gain: parseFloat(form.estimated_gain),
        from_date: form.from_date,
        to_date: form.to_date,
        notes: form.notes,
      })
      setResult(r.data)
      if (onGenerated) onGenerated(r.data)
    } catch (e) {
      toast.error('Case generation failed')
    } finally {
      setLoading(false)
    }
  }

  return (
    <AnimatePresence>
      <motion.div
        initial={{ opacity:0 }}
        animate={{ opacity:1 }}
        exit={{ opacity:0 }}
        style={{
          position:'fixed', inset:0,
          background:'rgba(0,0,0,0.85)',
          display:'flex', alignItems:'center', justifyContent:'center',
          zIndex:1000,
        }}
        onClick={onClose}
      >
        <motion.div
          initial={{ y:20, opacity:0 }}
          animate={{ y:0, opacity:1 }}
          exit={{ y:20, opacity:0 }}
          transition={{ duration:0.2 }}
          onClick={e => e.stopPropagation()}
          style={{
            width:620,
            background:'var(--bg-card)',
            border:'1px solid var(--border-bright)',
            padding:32,
            position:'relative',
            maxHeight:'90vh',
            overflowY:'auto',
          }}
        >
          {/* Close */}
          <button
            onClick={onClose}
            style={{
              position:'absolute', top:16, right:16,
              background:'transparent', border:'none',
              color:'var(--text-secondary)', fontSize:18, cursor:'pointer',
            }}
          >×</button>

          {/* Header */}
          <div style={{
            fontFamily:'var(--font-display)', fontWeight:700, fontSize:16,
            color:'var(--accent-green)', letterSpacing:2, marginBottom:4,
          }}>
            GENERATE SEBI CASE FILE
          </div>
          <div style={{ fontSize:10, color:'var(--text-dim)', fontFamily:'var(--font-mono)', letterSpacing:1, marginBottom:20 }}>
            ARGUS AUTOMATED ENFORCEMENT MODULE
          </div>

          {/* Alert summary */}
          <div style={{
            background:'var(--bg-surface)', border:'1px solid var(--border)',
            padding:16, marginBottom:20,
            display:'flex', gap:16, alignItems:'center',
          }}>
            <div>
              <div style={{ fontFamily:'var(--font-mono)', fontWeight:600, fontSize:14, color:'var(--text-primary)' }}>
                {alert.scrip}
              </div>
              <SchemeBadge type={alert.scheme_type} />
            </div>
            <div style={{ marginLeft:'auto', textAlign:'right' }}>
              <div style={{
                fontFamily:'var(--font-mono)', fontWeight:600, fontSize:22,
                color: alert.impossibility_score >= 8 ? 'var(--accent-red)' : 'var(--accent-amber)',
              }}>
                {alert.impossibility_score.toFixed(1)}/10
              </div>
              <div style={{ fontSize:9, color:'var(--text-dim)', letterSpacing:1 }}>OVERALL SCORE</div>
            </div>
          </div>

          {/* Score breakdown */}
          <div style={{ marginBottom:20 }}>
            <ScoreBar label="GNN COORDINATION" score={alert.gnn_score ?? 0} weight={35} />
            <ScoreBar label="DNA ANOMALY"      score={alert.dna_score ?? 0} weight={25} />
            <ScoreBar label="CROSS-MARKET"     score={alert.cross_market_score ?? 0} weight={15} />
            <ScoreBar label="ZERO-DAY"         score={alert.zero_day_score ?? 0} weight={25} />
          </div>

          {result ? (
            /* Success state */
            <div style={{ textAlign:'center', padding:24 }}>
              <div style={{ color:'var(--accent-green)', fontSize:11, letterSpacing:1, marginBottom:8 }}>
                CASE FILE GENERATED
              </div>
              <div style={{
                fontFamily:'var(--font-display)', fontWeight:700, fontSize:18,
                color:'var(--accent-green)', letterSpacing:3, marginBottom:16,
              }}>
                {result.case_number}
              </div>
              <a
                href={result.pdf_url}
                target="_blank"
                rel="noreferrer"
                style={{
                  display:'inline-block',
                  background:'var(--accent-green)', color:'#000',
                  fontFamily:'var(--font-display)', fontWeight:700, fontSize:13,
                  padding:'10px 32px', letterSpacing:1,
                  border:'none', cursor:'pointer',
                }}
              >
                DOWNLOAD PDF ({result.file_size_kb ?? 284} KB) →
              </a>
            </div>
          ) : (
            /* Form */
            <div style={{ display:'flex', flexDirection:'column', gap:14 }}>
              <div>
                <label style={{ fontFamily:'var(--font-mono)', fontSize:10, color:'var(--text-secondary)', letterSpacing:1, display:'block', marginBottom:4 }}>
                  ENTITY NAMES (comma separated)
                </label>
                <input
                  style={{ width:'100%', borderRadius:0 }}
                  value={form.entity_names}
                  onChange={e => setForm(f => ({ ...f, entity_names:e.target.value }))}
                />
              </div>
              <div>
                <label style={{ fontFamily:'var(--font-mono)', fontSize:10, color:'var(--text-secondary)', letterSpacing:1, display:'block', marginBottom:4 }}>
                  ESTIMATED ILLEGAL GAIN (₹)
                </label>
                <input
                  type="number"
                  style={{ width:'100%', borderRadius:0 }}
                  value={form.estimated_gain}
                  onChange={e => setForm(f => ({ ...f, estimated_gain:e.target.value }))}
                />
              </div>
              <div style={{ display:'grid', gridTemplateColumns:'1fr 1fr', gap:12 }}>
                <div>
                  <label style={{ fontFamily:'var(--font-mono)', fontSize:10, color:'var(--text-secondary)', letterSpacing:1, display:'block', marginBottom:4 }}>FROM DATE</label>
                  <input type="date" style={{ width:'100%', borderRadius:0 }} value={form.from_date} onChange={e=>setForm(f=>({...f,from_date:e.target.value}))} />
                </div>
                <div>
                  <label style={{ fontFamily:'var(--font-mono)', fontSize:10, color:'var(--text-secondary)', letterSpacing:1, display:'block', marginBottom:4 }}>TO DATE</label>
                  <input type="date" style={{ width:'100%', borderRadius:0 }} value={form.to_date} onChange={e=>setForm(f=>({...f,to_date:e.target.value}))} />
                </div>
              </div>
              <div>
                <label style={{ fontFamily:'var(--font-mono)', fontSize:10, color:'var(--text-secondary)', letterSpacing:1, display:'block', marginBottom:4 }}>ANALYST NOTES</label>
                <textarea
                  rows={3}
                  style={{ width:'100%', resize:'vertical', borderRadius:0 }}
                  value={form.notes}
                  onChange={e=>setForm(f=>({...f,notes:e.target.value}))}
                  placeholder="Add enforcement notes, evidence summary..."
                />
              </div>

              <button
                onClick={handleGenerate}
                disabled={loading}
                style={{
                  width:'100%', padding:14,
                  background: loading ? 'var(--text-dim)' : 'var(--accent-green)',
                  color:'#000',
                  fontFamily:'var(--font-display)', fontWeight:700, fontSize:14,
                  border:'none', cursor: loading ? 'not-allowed' : 'pointer',
                  letterSpacing: 1,
                  display:'flex', alignItems:'center', justifyContent:'center', gap:8,
                }}
              >
                {loading ? (
                  <>
                    <span style={{ animation:'spin 1s linear infinite', display:'inline-block' }}>⟳</span>
                    GENERATING...
                  </>
                ) : 'GENERATE CASE FILE →'}
              </button>
            </div>
          )}
        </motion.div>
      </motion.div>
    </AnimatePresence>
  )
}
