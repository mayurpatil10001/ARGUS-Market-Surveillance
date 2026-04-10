import { useQuery } from 'react-query'
import { motion } from 'framer-motion'
import {
  BarChart, Bar, XAxis, YAxis, Tooltip, Cell, ResponsiveContainer,
  PieChart, Pie, Legend,
} from 'recharts'
import { api } from '../api/client'
import MetricCard from '../components/MetricCard'
import ThreatBadge from '../components/ThreatBadge'

// ── Color helpers ──────────────────────────────────────────────────────────────
const PLATFORM_COLORS = {
  twitter:  '#1d9bf0',
  reddit:   '#ff4500',
  telegram: '#2aabee',
  web:      '#00ff88',
  email:    '#a78bfa',
  other:    '#71717a',
}

const CATEGORY_COLORS = {
  coordinated_attack: '#ff3333',
  malicious_content:  '#ff8c00',
  phishing:           '#ffe600',
  misinformation:     '#a000ff',
  platform_abuse:     '#3b82f6',
  novel_threat:       '#00ffff',
}

function scoreBarColor(avg) {
  if (avg >= 8) return '#ff3355'
  if (avg >= 7) return '#ffb300'
  return '#00ff88'
}

function peakColor(score) {
  if (score >= 8.5) return 'var(--accent-red)'
  if (score >= 7.5) return 'var(--accent-amber)'
  return 'var(--accent-green)'
}

const CustomBarTooltip = ({ active, payload, label }) => {
  if (!active || !payload?.length) return null
  return (
    <div style={{
      background:'var(--bg-card)', border:'1px solid var(--border-bright)',
      padding:'8px 12px', fontFamily:'JetBrains Mono, monospace', fontSize:11,
    }}>
      <div style={{ color:'var(--text-primary)', marginBottom:4 }}>{label}</div>
      <div style={{ color:'var(--accent-green)' }}>{payload[0].value} threats</div>
      <div style={{ color:'var(--text-secondary)' }}>Avg: {payload[0].payload.avg_score?.toFixed(1)}/10</div>
    </div>
  )
}

const CustomPieLabel = ({ name, percent }) =>
  `${(percent*100).toFixed(0)}%`

export default function WeeklySummary() {
  const { data: sum, isLoading } = useQuery(
    'weekly_summary',
    () => api.weeklySummary(),
    { select: r => r.data }
  )

  const today = new Date()
  const from  = new Date(today - 7*86400000).toLocaleDateString('en-IN', { day:'2-digit', month:'short' })
  const to    = today.toLocaleDateString('en-IN', { day:'2-digit', month:'short', year:'numeric' })

  if (isLoading) return (
    <div style={{ display:'grid', gap:20 }}>
      <div style={{ display:'grid', gridTemplateColumns:'repeat(4,1fr)', gap:16 }}>
        {Array.from({length:4}).map((_,i) => <div key={i} className="skeleton" style={{ height:100 }} />)}
      </div>
      <div className="skeleton" style={{ height:300 }} />
    </div>
  )

  if (!sum) return null

  // Build category distribution for pie chart
  const categoryData = Object.entries(sum.by_category || {}).map(([name, value]) => ({
    name: name.replace(/_/g, ' ').toUpperCase(),
    value,
    color: CATEGORY_COLORS[name] || '#71717a',
  }))

  // Build platform data for bar chart
  const platformData = (sum.top_platforms || []).map(p => ({
    platform: (p.platform || p.scrip || 'unknown').toUpperCase(),
    count: p.count,
    color: PLATFORM_COLORS[(p.platform || '').toLowerCase()] || '#71717a',
  }))

  // Fallback to legacy top_scrips if no platform data
  const legacyScripData = (sum.top_flagged_scrips || []).map(s => ({
    platform: (s.scrip || 'unknown').toUpperCase(),
    count: s.count,
    color: '#00ff88',
  }))

  const displayPlatformData = platformData.length > 0 ? platformData : legacyScripData

  return (
    <motion.div initial={{ opacity:0, y:-8 }} animate={{ opacity:1, y:0 }} transition={{ duration:0.2 }}>
      {/* Header */}
      <div style={{ marginBottom:24 }}>
        <div style={{ fontFamily:'var(--font-display)', fontWeight:700, fontSize:20, color:'var(--text-primary)', letterSpacing:3 }}>
          WEEKLY THREAT INTELLIGENCE REPORT
        </div>
        <div style={{ fontFamily:'var(--font-mono)', fontSize:11, color:'var(--text-secondary)', marginTop:4 }}>
          {from} — {to} · Generated: {new Date().toLocaleTimeString('en-IN', { hour12:false })} IST · SENTINEL v2.0
        </div>
      </div>

      {/* Metric cards — PS-402 fields */}
      <div style={{ display:'grid', gridTemplateColumns:'repeat(4,1fr)', gap:16, marginBottom:24 }}>
        <MetricCard label="Total Threats"      value={sum.total_threats ?? sum.total_alerts}    color="var(--accent-red)" />
        <MetricCard label="Resolved"           value={sum.resolved}                              color="var(--accent-green)" />
        <MetricCard label="Mitigation Rate"    value={sum.mitigation_rate ?? 0}                  color="var(--accent-amber)" unit="%" />
        <MetricCard label="False Positive Rate" value={sum.false_positive_rate_pct ?? 0}         color="var(--accent-blue)" unit="%" />
      </div>

      {/* Charts row */}
      <div style={{ display:'grid', gridTemplateColumns:'1fr 1fr', gap:20, marginBottom:24 }}>

        {/* Platform breakdown bar chart — PS-402 */}
        <div style={{ background:'var(--bg-card)', border:'1px solid var(--border)', padding:20 }}>
          <div style={{ fontFamily:'var(--font-mono)', fontSize:9, color:'var(--text-dim)', letterSpacing:2, marginBottom:16 }}>
            THREATS BY PLATFORM (7 DAYS)
          </div>
          <div className="chart-grid-bg" style={{ borderRadius:0 }}>
            <ResponsiveContainer width="100%" height={220}>
              <BarChart data={displayPlatformData} margin={{ top:4, right:4, bottom:0, left:-20 }}>
                <XAxis dataKey="platform" tick={{ fontFamily:'JetBrains Mono, monospace', fontSize:10, fill:'var(--text-secondary)' }} axisLine={false} tickLine={false} />
                <YAxis tick={{ fontFamily:'JetBrains Mono, monospace', fontSize:10, fill:'var(--text-secondary)' }} axisLine={false} tickLine={false} />
                <Tooltip content={<CustomBarTooltip />} />
                <Bar dataKey="count" radius={0}>
                  {displayPlatformData.map((d, i) => (
                    <Cell key={i} fill={d.color} />
                  ))}
                </Bar>
              </BarChart>
            </ResponsiveContainer>
          </div>
        </div>

        {/* Threat category pie — PS-402 */}
        <div style={{ background:'var(--bg-card)', border:'1px solid var(--border)', padding:20 }}>
          <div style={{ fontFamily:'var(--font-mono)', fontSize:9, color:'var(--text-dim)', letterSpacing:2, marginBottom:16 }}>
            THREAT CATEGORY DISTRIBUTION
          </div>
          <ResponsiveContainer width="100%" height={220}>
            <PieChart>
              <Pie
                data={categoryData.length > 0 ? categoryData : [{ name:'NO DATA', value:1, color:'#71717a' }]}
                cx="50%" cy="50%"
                innerRadius={55} outerRadius={85}
                dataKey="value"
                label={CustomPieLabel}
                labelLine={false}
              >
                {(categoryData.length > 0 ? categoryData : [{ color:'#71717a' }]).map((d, i) => (
                  <Cell key={i} fill={d.color} />
                ))}
              </Pie>
              <Legend
                iconType="circle"
                iconSize={8}
                formatter={(v) => (
                  <span style={{ fontFamily:'JetBrains Mono, monospace', fontSize:10, color:'var(--text-secondary)' }}>{v}</span>
                )}
              />
            </PieChart>
          </ResponsiveContainer>
        </div>
      </div>

      {/* Top platforms / entities table */}
      <div style={{ background:'var(--bg-card)', border:'1px solid var(--border)', marginBottom:24 }}>
        <div style={{ padding:'12px 16px', borderBottom:'1px solid var(--border)', fontFamily:'var(--font-mono)', fontSize:9, color:'var(--text-dim)', letterSpacing:2 }}>
          TOP THREAT SOURCES & PLATFORMS
        </div>
        <div style={{
          display:'grid', gridTemplateColumns:'140px 80px 100px 100px 160px 120px',
          padding:'8px 16px', gap:8,
          borderBottom:'1px solid var(--border-bright)',
          fontFamily:'var(--font-mono)', fontSize:9, color:'var(--text-dim)', letterSpacing:1,
          background:'var(--bg-surface)',
        }}>
          {['PLATFORM','THREATS','AVG SCORE','PEAK SCORE','THREAT TYPE','ACTION'].map(h => <div key={h}>{h}</div>)}
        </div>
        {(sum.top_platforms && sum.top_platforms.length > 0
          ? sum.top_platforms
          : (sum.top_flagged_scrips || []).map(s => ({ platform: s.scrip, count: s.count, avg_score: 0, peak_score: 0, threat_category: 'novel_threat' }))
        ).map((row, i) => (
          <div key={row.platform || i} style={{
            display:'grid', gridTemplateColumns:'140px 80px 100px 100px 160px 120px',
            padding:'10px 16px', gap:8,
            borderLeft: `2px solid ${PLATFORM_COLORS[(row.platform||'').toLowerCase()] || 'var(--accent-green)'}`,
            borderBottom:'1px solid var(--border)',
            fontFamily:'var(--font-mono)', fontSize:11,
          }}>
            <span style={{ fontWeight:600 }}>{(row.platform || row.scrip || '—').toUpperCase()}</span>
            <span style={{ color:'var(--text-secondary)' }}>{row.count}</span>
            <span style={{ color: peakColor(row.avg_score || 0) }}>{(row.avg_score || 0).toFixed(1)}</span>
            <span style={{ color: peakColor(row.peak_score || 0), fontWeight:600 }}>{(row.peak_score || 0).toFixed(1)}</span>
            <ThreatBadge type={row.threat_category || row.scheme_type || 'novel_threat'} />
            <button style={{
              fontFamily:'var(--font-mono)', fontSize:9, letterSpacing:1,
              color:'var(--accent-green)', background:'transparent',
              border:'1px solid rgba(0,255,136,0.3)', padding:'3px 8px', cursor:'pointer',
            }}>
              INVESTIGATE →
            </button>
          </div>
        ))}
      </div>

      {/* PS-402 Category breakdown table */}
      {Object.keys(sum.by_category || {}).length > 0 && (
        <div style={{ background:'var(--bg-card)', border:'1px solid var(--border)', marginBottom:24 }}>
          <div style={{ padding:'12px 16px', borderBottom:'1px solid var(--border)', fontFamily:'var(--font-mono)', fontSize:9, color:'var(--text-dim)', letterSpacing:2 }}>
            THREAT CATEGORIES BREAKDOWN (PS-402)
          </div>
          {Object.entries(sum.by_category).map(([cat, count]) => (
            <div key={cat} style={{
              display:'grid', gridTemplateColumns:'200px 1fr 80px',
              padding:'10px 16px', gap:16,
              borderLeft:`2px solid ${CATEGORY_COLORS[cat] || '#71717a'}`,
              borderBottom:'1px solid var(--border)',
              alignItems:'center',
            }}>
              <ThreatBadge type={cat} />
              <div style={{ height:8, background:'var(--bg-surface)', borderRadius:2, overflow:'hidden' }}>
                <div style={{
                  height:'100%',
                  width:`${Math.min(100, (count / Math.max(sum.total_threats ?? sum.total_alerts, 1)) * 100)}%`,
                  background: CATEGORY_COLORS[cat] || '#71717a',
                  borderRadius:2,
                }} />
              </div>
              <span style={{ fontFamily:'var(--font-mono)', fontSize:11, color:'var(--text-secondary)', textAlign:'right' }}>{count}</span>
            </div>
          ))}
        </div>
      )}

      {/* Export */}
      <div style={{ display:'flex', justifyContent:'flex-end' }}>
        <button style={{
          background:'transparent', color:'var(--accent-green)',
          border:'1px solid rgba(0,255,136,0.4)',
          fontFamily:'var(--font-mono)', fontSize:11, letterSpacing:1,
          padding:'10px 24px', cursor:'pointer',
        }}
        onClick={() => alert('PDF export requires backend connection')}
        >
          EXPORT THREAT REPORT PDF →
        </button>
      </div>
    </motion.div>
  )
}
