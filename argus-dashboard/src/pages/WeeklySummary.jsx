import { useQuery } from 'react-query'
import { motion } from 'framer-motion'
import {
  BarChart, Bar, XAxis, YAxis, Tooltip, Cell, ResponsiveContainer,
  PieChart, Pie, Legend,
} from 'recharts'
import { api } from '../api/client'
import MetricCard from '../components/MetricCard'
import SchemeBadge from '../components/SchemeBadge'

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
      <div style={{ color:'var(--accent-green)' }}>{payload[0].value} alerts</div>
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

  return (
    <motion.div initial={{ opacity:0, y:-8 }} animate={{ opacity:1, y:0 }} transition={{ duration:0.2 }}>
      {/* Header */}
      <div style={{ marginBottom:24 }}>
        <div style={{ fontFamily:'var(--font-display)', fontWeight:700, fontSize:20, color:'var(--text-primary)', letterSpacing:3 }}>
          WEEKLY SURVEILLANCE REPORT
        </div>
        <div style={{ fontFamily:'var(--font-mono)', fontSize:11, color:'var(--text-secondary)', marginTop:4 }}>
          {from} — {to} · Generated: {new Date().toLocaleTimeString('en-IN', { hour12:false })} IST
        </div>
      </div>

      {/* Metric cards */}
      <div style={{ display:'grid', gridTemplateColumns:'repeat(4,1fr)', gap:16, marginBottom:24 }}>
        <MetricCard label="Total Alerts"        value={sum.total_alerts}         color="var(--accent-red)" />
        <MetricCard label="Resolved"            value={sum.resolved_alerts}      color="var(--accent-green)" />
        <MetricCard label="False Positive Rate" value={sum.false_positive_rate}  color="var(--accent-amber)" unit="%" />
        <MetricCard label="Cases Filed"         value={sum.cases_filed}          color="var(--accent-blue)" />
      </div>

      {/* Charts row */}
      <div style={{ display:'grid', gridTemplateColumns:'1fr 1fr', gap:20, marginBottom:24 }}>
        {/* Daily bar chart */}
        <div style={{ background:'var(--bg-card)', border:'1px solid var(--border)', padding:20 }}>
          <div style={{ fontFamily:'var(--font-mono)', fontSize:9, color:'var(--text-dim)', letterSpacing:2, marginBottom:16 }}>
            DAILY ALERT VOLUME (7 DAYS)
          </div>
          <div className="chart-grid-bg" style={{ borderRadius:0 }}>
            <ResponsiveContainer width="100%" height={220}>
              <BarChart data={sum.daily_alerts} margin={{ top:4, right:4, bottom:0, left:-20 }}>
                <XAxis dataKey="day" tick={{ fontFamily:'JetBrains Mono, monospace', fontSize:10, fill:'var(--text-secondary)' }} axisLine={false} tickLine={false} />
                <YAxis tick={{ fontFamily:'JetBrains Mono, monospace', fontSize:10, fill:'var(--text-secondary)' }} axisLine={false} tickLine={false} />
                <Tooltip content={<CustomBarTooltip />} />
                <Bar dataKey="count" radius={0}>
                  {sum.daily_alerts.map((d, i) => (
                    <Cell key={i} fill={scoreBarColor(d.avg_score)} />
                  ))}
                </Bar>
              </BarChart>
            </ResponsiveContainer>
          </div>
        </div>

        {/* Pie chart */}
        <div style={{ background:'var(--bg-card)', border:'1px solid var(--border)', padding:20 }}>
          <div style={{ fontFamily:'var(--font-mono)', fontSize:9, color:'var(--text-dim)', letterSpacing:2, marginBottom:16 }}>
            SCHEME TYPE DISTRIBUTION
          </div>
          <ResponsiveContainer width="100%" height={220}>
            <PieChart>
              <Pie
                data={sum.scheme_distribution}
                cx="50%" cy="50%"
                innerRadius={55} outerRadius={85}
                dataKey="value"
                label={CustomPieLabel}
                labelLine={false}
              >
                {sum.scheme_distribution.map((d, i) => (
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

      {/* Top scrips */}
      <div style={{ background:'var(--bg-card)', border:'1px solid var(--border)', marginBottom:24 }}>
        <div style={{ padding:'12px 16px', borderBottom:'1px solid var(--border)', fontFamily:'var(--font-mono)', fontSize:9, color:'var(--text-dim)', letterSpacing:2 }}>
          TOP MANIPULATED SCRIPS
        </div>
        <div style={{
          display:'grid', gridTemplateColumns:'140px 80px 100px 100px 160px 120px',
          padding:'8px 16px', gap:8,
          borderBottom:'1px solid var(--border-bright)',
          fontFamily:'var(--font-mono)', fontSize:9, color:'var(--text-dim)', letterSpacing:1,
          background:'var(--bg-surface)',
        }}>
          {['SCRIP','ALERTS','AVG SCORE','PEAK SCORE','SCHEME TYPE','ACTION'].map(h => <div key={h}>{h}</div>)}
        </div>
        {sum.top_scrips.map(row => (
          <div key={row.scrip} style={{
            display:'grid', gridTemplateColumns:'140px 80px 100px 100px 160px 120px',
            padding:'10px 16px', gap:8,
            borderLeft: `2px solid ${peakColor(row.peak_score)}`,
            borderBottom:'1px solid var(--border)',
            fontFamily:'var(--font-mono)', fontSize:11,
          }}>
            <span style={{ fontWeight:600 }}>{row.scrip}</span>
            <span style={{ color:'var(--text-secondary)' }}>{row.alerts}</span>
            <span style={{ color:peakColor(row.avg_score) }}>{row.avg_score.toFixed(1)}</span>
            <span style={{ color:peakColor(row.peak_score), fontWeight:600 }}>{row.peak_score.toFixed(1)}</span>
            <SchemeBadge type={row.scheme_type} />
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

      {/* Performance metrics */}
      <div style={{ display:'grid', gridTemplateColumns:'repeat(3,1fr)', gap:16, marginBottom:24 }}>
        {[
          { label:'AVG DETECTION TIME', value: sum.detection_metrics.avg_detection_time_mins, unit:'MIN', color:'var(--accent-green)' },
          { label:'SENT TO ENFORCEMENT', value: sum.detection_metrics.cases_sent_to_enforcement, unit:'CASES', color:'var(--accent-blue)' },
          { label:'ALERT RESOLUTION RATE', value: sum.detection_metrics.alert_resolution_rate, unit:'%', color:'var(--accent-amber)' },
        ].map(({ label, value, unit, color }) => (
          <div key={label} style={{ background:'var(--bg-card)', border:'1px solid var(--border)', padding:16, borderLeft:`2px solid ${color}` }}>
            <div style={{ fontFamily:'var(--font-mono)', fontSize:9, color:'var(--text-secondary)', letterSpacing:2, marginBottom:8 }}>{label}</div>
            <div style={{ fontFamily:'var(--font-mono)', fontWeight:600, fontSize:24, color }}>
              {value} <span style={{ fontSize:12, color:'var(--text-secondary)' }}>{unit}</span>
            </div>
          </div>
        ))}
      </div>

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
          EXPORT WEEKLY REPORT PDF →
        </button>
      </div>
    </motion.div>
  )
}
