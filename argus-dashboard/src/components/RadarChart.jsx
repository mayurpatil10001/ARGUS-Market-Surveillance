import {
  Radar, RadarChart as RC, PolarGrid, PolarAngleAxis, ResponsiveContainer,
} from 'recharts'

const AXES = ['FREQUENCY','VOLUME','PRICE_IMPACT','TIMING','DIVERSITY','AGGRESSION','CONSISTENCY','ANOMALY']

export default function RadarChart({ dna = [], label }) {
  const data = AXES.map((axis, i) => ({ axis, value: (dna[i] ?? 0) * 100 }))

  return (
    <div style={{ background:'var(--bg-card)', padding:16 }}>
      {label && (
        <div style={{
          fontFamily:'var(--font-mono)', fontSize:9, color:'var(--text-dim)',
          letterSpacing:2, marginBottom:8,
        }}>
          {label}
        </div>
      )}
      <ResponsiveContainer width="100%" height={280}>
        <RC cx="50%" cy="50%" outerRadius={90} data={data}>
          <PolarGrid stroke="var(--border-bright)" radialLines={true} />
          <PolarAngleAxis
            dataKey="axis"
            tick={{
              fontFamily:'JetBrains Mono, monospace',
              fontSize: 9,
              fill: 'var(--text-secondary)',
              letterSpacing: 1,
            }}
          />
          <Radar
            name="DNA"
            dataKey="value"
            stroke="var(--accent-green)"
            fill="var(--accent-green)"
            fillOpacity={0.18}
            strokeWidth={1.5}
          />
        </RC>
      </ResponsiveContainer>
    </div>
  )
}
