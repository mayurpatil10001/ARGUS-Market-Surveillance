import { useState } from 'react'
import { useQuery } from 'react-query'
import { motion } from 'framer-motion'
import { BarChart, Bar, XAxis, YAxis, ReferenceLine, Cell, ResponsiveContainer, Tooltip } from 'recharts'
import { api } from '../api/client'
import RadarChart from '../components/RadarChart'
import ScoreGauge from '../components/ScoreGauge'

function simColor(sim) {
  if (sim >= 85) return 'var(--accent-red)'
  if (sim >= 70) return 'var(--accent-amber)'
  return 'var(--accent-green)'
}

export default function AccountDNA() {
  const [accountId, setAccountId] = useState('')
  const [queried, setQueried]     = useState('')
  const [tradePage, setTradePage] = useState(1)
  const TPER = 10

  const { data: dnaData, isLoading: dnaLoading, isError: dnaError } = useQuery(
    ['dna', queried],
    () => api.getAccountDNA(queried),
    { enabled: !!queried, select: r => r.data }
  )

  const { data: tradeData, isLoading: tradeLoading } = useQuery(
    ['trades', queried],
    () => api.getAccountTrades(queried),
    { enabled: !!queried, select: r => r.data }
  )

  const trades = tradeData?.trades || []
  const tradePaged = trades.slice((tradePage-1)*TPER, tradePage*TPER)
  const tradePages = Math.ceil(trades.length / TPER)

  const handleSearch = () => { if (accountId.trim()) setQueried(accountId.trim()) }

  return (
    <motion.div initial={{ opacity:0, y:-8 }} animate={{ opacity:1, y:0 }} transition={{ duration:0.2 }}>
      {/* Search */}
      <div style={{
        display:'flex', gap:12, marginBottom:24,
        padding:'16px', background:'var(--bg-card)', border:'1px solid var(--border)',
      }}>
        <input
          style={{ flex:1, fontSize:13 }}
          placeholder="ENTER ACCOUNT ID (e.g. COLL_000)"
          value={accountId}
          onChange={e => setAccountId(e.target.value)}
          onKeyDown={e => e.key==='Enter' && handleSearch()}
        />
        <button onClick={handleSearch} style={{
          background:'var(--accent-green)', color:'#000',
          fontFamily:'var(--font-display)', fontWeight:700, fontSize:13,
          border:'none', padding:'0 24px', letterSpacing:1, cursor:'pointer',
        }}>
          ANALYZE →
        </button>
      </div>

      {dnaLoading && (
        <div style={{ display:'grid', gridTemplateColumns:'1fr 1fr', gap:20, marginBottom:20 }}>
          {[1,2].map(i => (
            <div key={i} className="skeleton" style={{ height:320 }} />
          ))}
        </div>
      )}

      {dnaError && (
        <div style={{ padding:40, textAlign:'center', color:'var(--accent-red)', fontFamily:'var(--font-mono)', border:'1px solid var(--border)' }}>
          ACCOUNT NOT FOUND — NO DATA IN SURVEILLANCE DATABASE
        </div>
      )}

      {dnaData && !dnaLoading && (
        <>
          {/* Account header */}
          <div style={{
            background:'var(--bg-card)', border:'1px solid var(--border)',
            borderLeft:`2px solid ${dnaData.flagged ? 'var(--accent-red)' : 'var(--accent-green)'}`,
            padding:'16px 20px', marginBottom:20,
            display:'flex', alignItems:'center', gap:20,
          }}>
            <div>
              <div style={{ fontFamily:'var(--font-display)', fontWeight:700, fontSize:18, color:'var(--text-primary)', letterSpacing:2 }}>
                {dnaData.id}
              </div>
              <div style={{ fontFamily:'var(--font-mono)', fontSize:11, color:'var(--text-secondary)', marginTop:4 }}>
                {dnaData.broker} · DNA updated {new Date(dnaData.dna_updated).toLocaleTimeString('en-IN', { hour12:false })}
              </div>
            </div>
            <div style={{ marginLeft:12 }}>
              <span style={{
                fontFamily:'var(--font-mono)', fontSize:10, letterSpacing:1,
                color: dnaData.flagged ? 'var(--accent-red)' : 'var(--accent-green)',
                background: dnaData.flagged ? 'rgba(255,51,85,0.12)' : 'rgba(0,255,136,0.12)',
                border: `1px solid ${dnaData.flagged ? 'rgba(255,51,85,0.3)' : 'rgba(0,255,136,0.3)'}`,
                padding:'3px 10px',
              }}>
                {dnaData.flagged ? '⚑ FLAGGED' : '✓ CLEAN'}
              </span>
            </div>
            <div style={{ marginLeft:'auto' }}>
              <ScoreGauge score={dnaData.anomaly_score ?? 0} label="ANOMALY SCORE" />
            </div>
          </div>

          {/* DNA + Similarity */}
          <div style={{ display:'grid', gridTemplateColumns:'1fr 1fr', gap:20, marginBottom:20 }}>
            <RadarChart dna={dnaData.dna_vector ?? []} label="BEHAVIORAL DNA PROFILE" />

            {/* Fraudster similarity */}
            <div style={{ background:'var(--bg-card)', border:'1px solid var(--border)', padding:16 }}>
              <div style={{ fontFamily:'var(--font-mono)', fontSize:9, color:'var(--text-dim)', letterSpacing:2, marginBottom:12 }}>
                KNOWN FRAUDSTER SIMILARITY
              </div>
              <ResponsiveContainer width="100%" height={220}>
                <BarChart
                  layout="vertical"
                  data={dnaData.fraudster_matches ?? []}
                  margin={{ left:0, right:40, top:0, bottom:0 }}
                >
                  <XAxis type="number" domain={[0,100]} tick={{ fontFamily:'JetBrains Mono, monospace', fontSize:9, fill:'var(--text-secondary)' }} />
                  <YAxis type="category" dataKey="name" width={100} tick={{ fontFamily:'JetBrains Mono, monospace', fontSize:9, fill:'var(--text-secondary)' }} />
                  <Tooltip
                    contentStyle={{ background:'var(--bg-card)', border:'1px solid var(--border-bright)', fontFamily:'JetBrains Mono, monospace', fontSize:11 }}
                    formatter={(v, _, props) => [`${v.toFixed(1)}% similarity`, props.payload.scheme]}
                  />
                  <ReferenceLine x={85} stroke="var(--accent-red)" strokeDasharray="3 3" label={{ value:'THRESHOLD', fill:'var(--accent-red)', fontSize:8, fontFamily:'JetBrains Mono, monospace' }} />
                  <Bar dataKey="similarity" radius={0}>
                    {(dnaData.fraudster_matches ?? []).map((m, i) => (
                      <Cell key={i} fill={simColor(m.similarity)} />
                    ))}
                  </Bar>
                </BarChart>
              </ResponsiveContainer>
            </div>
          </div>

          {/* Trade history */}
          <div style={{ background:'var(--bg-card)', border:'1px solid var(--border)' }}>
            <div style={{
              padding:'12px 16px',
              borderBottom:'1px solid var(--border)',
              fontFamily:'var(--font-mono)', fontSize:10, color:'var(--text-dim)', letterSpacing:2,
            }}>
              TRADE HISTORY ({trades.length} records)
            </div>
            <div style={{
              display:'grid',
              gridTemplateColumns:'160px 120px 60px 90px 90px 90px 80px',
              padding:'8px 16px', gap:8,
              borderBottom:'1px solid var(--border-bright)',
              background:'var(--bg-surface)',
              fontSize:9, color:'var(--text-dim)', fontFamily:'var(--font-mono)', letterSpacing:1,
            }}>
              {['TIMESTAMP','SCRIP','SIDE','PRICE','VOLUME','EXCHANGE','FLAG'].map(h => <div key={h}>{h}</div>)}
            </div>
            {tradeLoading && Array.from({length:5}).map((_,i) => (
              <div key={i} className="skeleton" style={{ height:36, margin:'2px 16px' }} />
            ))}
            {tradePaged.map(t => (
              <div key={t.id} style={{
                display:'grid',
                gridTemplateColumns:'160px 120px 60px 90px 90px 90px 80px',
                padding:'10px 16px', gap:8,
                borderLeft: t.suspicious ? '2px solid var(--accent-red)' : '2px solid transparent',
                borderBottom:'1px solid var(--border)',
                fontFamily:'var(--font-mono)', fontSize:11,
                background: t.suspicious ? 'rgba(255,51,85,0.03)' : 'transparent',
              }}>
                <span style={{ color:'var(--text-secondary)' }}>{new Date(t.timestamp).toLocaleString('en-IN',{hour12:false})}</span>
                <span style={{ color:'var(--text-primary)' }}>{t.scrip}</span>
                <span style={{ color: t.side==='BUY' ? 'var(--accent-green)' : 'var(--accent-red)' }}>{t.side}</span>
                <span style={{ color:'var(--text-primary)' }}>₹{t.price}</span>
                <span style={{ color:'var(--text-secondary)' }}>{t.volume.toLocaleString()}</span>
                <span style={{ color:'var(--text-dim)' }}>{t.exchange}</span>
                <span style={{ color: t.suspicious ? 'var(--accent-red)' : 'var(--text-dim)', fontSize:9 }}>
                  {t.suspicious ? '⚑ SUSP' : '—'}
                </span>
              </div>
            ))}
            {tradePages > 1 && (
              <div style={{ display:'flex', gap:8, padding:'12px 16px' }}>
                {Array.from({length:tradePages},(_,i)=>i+1).map(n => (
                  <button key={n} onClick={()=>setTradePage(n)} style={{
                    width:28, height:28,
                    background: tradePage===n ? 'var(--accent-green)' : 'var(--bg-surface)',
                    color: tradePage===n ? '#000' : 'var(--text-secondary)',
                    border:'1px solid var(--border)', fontFamily:'var(--font-mono)', fontSize:10, cursor:'pointer',
                  }}>{n}</button>
                ))}
              </div>
            )}
          </div>
        </>
      )}

      {!queried && (
        <div style={{
          padding:80, textAlign:'center',
          fontFamily:'var(--font-mono)', color:'var(--text-dim)',
          letterSpacing:2, fontSize:12,
          border:'1px solid var(--border)', background:'var(--bg-card)',
        }}>
          ENTER AN ACCOUNT ID ABOVE TO BEGIN DNA ANALYSIS
        </div>
      )}
    </motion.div>
  )
}
