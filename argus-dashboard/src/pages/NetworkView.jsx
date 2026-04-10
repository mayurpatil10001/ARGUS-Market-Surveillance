import { useState } from 'react'
import { useQuery } from 'react-query'
import { motion } from 'framer-motion'
import { api } from '../api/client'
import NetworkGraph from '../components/NetworkGraph'
import * as d3 from 'd3'

const score2color = d3.scaleSequential().domain([0,10]).interpolator(d3.interpolateRgb('#00ff88','#ff3355'))

export default function NetworkView() {
  const [accountId, setAccountId] = useState('')
  const [queried, setQueried]     = useState('')
  const [selected, setSelected]   = useState(null)

  const { data: netData, isLoading } = useQuery(
    ['network', queried],
    () => api.getAccountNetwork(queried),
    { enabled: !!queried, select: r => r.data }
  )

  const nodes = netData?.nodes || []
  const edges = netData?.edges || []

  const flagged = nodes.filter(n => n.flagged).sort((a,b) => b.score - a.score)
  const maxEdges = Math.max(...edges.map(e => e.coincidence_count ?? 0), 1)
  const density  = nodes.length > 1
    ? ((edges.length / (nodes.length*(nodes.length-1)/2)) * 100).toFixed(1)
    : '0.0'
  const maxCluster = flagged.length

  return (
    <motion.div initial={{ opacity:0, y:-8 }} animate={{ opacity:1, y:0 }} transition={{ duration:0.2 }}>
      {/* Controls */}
      <div style={{
        display:'flex', gap:12, marginBottom:20,
        padding:'16px', background:'var(--bg-card)', border:'1px solid var(--border)',
      }}>
        <input
          style={{ flex:1, maxWidth:240, fontSize:13 }}
          placeholder="ACCOUNT ID (e.g. COLL_000)"
          value={accountId}
          onChange={e => setAccountId(e.target.value)}
          onKeyDown={e => e.key==='Enter' && setQueried(accountId.trim())}
        />
        <button
          onClick={() => setQueried(accountId.trim())}
          style={{
            background:'var(--accent-green)', color:'#000',
            fontFamily:'var(--font-display)', fontWeight:700, fontSize:13,
            border:'none', padding:'0 24px', cursor:'pointer', letterSpacing:1,
          }}
        >
          BUILD NETWORK →
        </button>
        {queried && (
          <button
            onClick={() => { setQueried(''); setSelected(null) }}
            style={{
              background:'transparent', color:'var(--text-secondary)',
              border:'1px solid var(--border)', fontFamily:'var(--font-mono)',
              fontSize:11, padding:'0 16px', cursor:'pointer',
            }}
          >
            RESET
          </button>
        )}
      </div>

      <div style={{ display:'grid', gridTemplateColumns:'1fr 300px', gap:20 }}>
        {/* Graph */}
        <div>
          {isLoading ? (
            <div className="skeleton" style={{ height:500 }} />
          ) : (
            <NetworkGraph nodes={nodes} edges={edges} />
          )}
        </div>

        {/* Right panel */}
        <div style={{ display:'flex', flexDirection:'column', gap:16 }}>
          {/* Stats */}
          <div style={{ background:'var(--bg-card)', border:'1px solid var(--border)', padding:16 }}>
            <div style={{ fontFamily:'var(--font-mono)', fontSize:9, color:'var(--text-dim)', letterSpacing:2, marginBottom:12 }}>
              NETWORK STATISTICS
            </div>
            {[
              ['TOTAL NODES',          nodes.length],
              ['TOTAL EDGES',          edges.length],
              ['FLAGGED NODES',        flagged.length],
              ['COORDINATION DENSITY', `${density}%`],
              ['MAX CLUSTER SIZE',     maxCluster],
            ].map(([l,v]) => (
              <div key={l} style={{ display:'flex', justifyContent:'space-between', marginBottom:8 }}>
                <span style={{ fontFamily:'var(--font-mono)', fontSize:10, color:'var(--text-secondary)' }}>{l}</span>
                <span style={{ fontFamily:'var(--font-mono)', fontSize:11, fontWeight:600, color:'var(--text-primary)' }}>{v}</span>
              </div>
            ))}
          </div>

          {/* Top flagged */}
          {flagged.length > 0 && (
            <div style={{ background:'var(--bg-card)', border:'1px solid var(--border)', padding:16 }}>
              <div style={{ fontFamily:'var(--font-mono)', fontSize:9, color:'var(--text-dim)', letterSpacing:2, marginBottom:12 }}>
                TOP FLAGGED ACCOUNTS
              </div>
              {flagged.slice(0,5).map(n => (
                <div key={n.id} style={{
                  display:'flex', alignItems:'center', gap:8, marginBottom:8,
                  padding:'6px 8px',
                  background: selected?.id === n.id ? 'var(--bg-surface)' : 'transparent',
                  cursor:'pointer',
                  borderLeft: selected?.id === n.id ? '2px solid var(--accent-green)' : '2px solid transparent',
                }}
                onClick={() => setSelected(n)}
                >
                  <div style={{ width:10, height:10, borderRadius:'50%', background:score2color(n.score), flexShrink:0 }} />
                  <span style={{ fontFamily:'var(--font-mono)', fontSize:11, flex:1 }}>{n.id}</span>
                  <span style={{
                    fontFamily:'var(--font-mono)', fontSize:9,
                    color: n.score >= 8 ? 'var(--accent-red)' : 'var(--accent-amber)',
                    background: n.score >= 8 ? 'rgba(255,51,85,0.1)' : 'rgba(255,179,0,0.1)',
                    padding:'1px 5px',
                  }}>
                    {n.score.toFixed(1)}
                  </span>
                </div>
              ))}
            </div>
          )}

          {/* Selected node detail */}
          {selected && (
            <div style={{ background:'var(--bg-card)', border:'1px solid var(--accent-green)', padding:16 }}>
              <div style={{ fontFamily:'var(--font-mono)', fontSize:9, color:'var(--text-dim)', letterSpacing:2, marginBottom:12 }}>
                SELECTED NODE
              </div>
              <div style={{ fontFamily:'var(--font-display)', fontWeight:700, fontSize:15, color:'var(--text-primary)', marginBottom:4 }}>
                {selected.id}
              </div>
              <div style={{ fontFamily:'var(--font-mono)', fontSize:11, color:'var(--text-secondary)', marginBottom:12 }}>
                Score: <span style={{ color:score2color(selected.score) }}>{selected.score.toFixed(2)}</span>
                {' · '}
                <span style={{ color: selected.flagged ? 'var(--accent-red)' : 'var(--accent-green)' }}>
                  {selected.flagged ? 'FLAGGED' : 'NORMAL'}
                </span>
              </div>
              <button
                onClick={() => window.location.hash = '#/dna'}
                style={{
                  fontFamily:'var(--font-mono)', fontSize:10, letterSpacing:1,
                  color:'var(--accent-green)', background:'transparent',
                  border:'1px solid rgba(0,255,136,0.3)', padding:'5px 12px', cursor:'pointer',
                }}
              >
                VIEW DNA →
              </button>
            </div>
          )}

          {/* Legend */}
          <div style={{ background:'var(--bg-card)', border:'1px solid var(--border)', padding:16 }}>
            <div style={{ fontFamily:'var(--font-mono)', fontSize:9, color:'var(--text-dim)', letterSpacing:2, marginBottom:10 }}>
              NODE SCORE LEGEND
            </div>
            {[[0,'#00ff88','LOW RISK (0-4)'],[4,'#ffb300','MEDIUM (4-7)'],[7,'#ff3355','HIGH RISK (7-10)']].map(([s,c,l]) => (
              <div key={l} style={{ display:'flex', alignItems:'center', gap:8, marginBottom:6 }}>
                <div style={{ width:12, height:12, borderRadius:'50%', background:c, flexShrink:0 }} />
                <span style={{ fontFamily:'var(--font-mono)', fontSize:10, color:'var(--text-secondary)' }}>{l}</span>
              </div>
            ))}
          </div>
        </div>
      </div>
    </motion.div>
  )
}
