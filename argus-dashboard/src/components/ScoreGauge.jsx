import { useEffect, useRef, useState } from 'react'

function scoreColor(score) {
  if (score >= 8) return '#ff3355'
  if (score >= 6) return '#ffb300'
  return '#00ff88'
}

export default function ScoreGauge({ score, label }) {
  const [progress, setProgress] = useState(0)
  const r = 54
  const cx = 70, cy = 75
  const startAngle = Math.PI
  const endAngle   = 2 * Math.PI
  const totalArc   = endAngle - startAngle
  const circumference = r * totalArc

  useEffect(() => {
    const t = setTimeout(() => setProgress(score / 10), 100)
    return () => clearTimeout(t)
  }, [score])

  const color = scoreColor(score)
  const offset = circumference * (1 - progress)

  const describeArc = (pct) => {
    const angle = startAngle + totalArc * pct
    const x = cx + r * Math.cos(angle)
    const y = cy + r * Math.sin(angle)
    return `M ${cx + r * Math.cos(startAngle)} ${cy + r * Math.sin(startAngle)} A ${r} ${r} 0 ${pct > 0.5 ? 1 : 0} 1 ${x} ${y}`
  }

  return (
    <div style={{ display:'flex', flexDirection:'column', alignItems:'center' }}>
      <svg width="140" height="90" viewBox="0 0 140 90">
        {/* Background arc */}
        <path
          d={describeArc(0.999)}
          fill="none"
          stroke="var(--border-bright)"
          strokeWidth="8"
          strokeLinecap="butt"
        />
        {/* Filled arc */}
        <path
          d={describeArc(0.999)}
          fill="none"
          stroke={color}
          strokeWidth="8"
          strokeLinecap="butt"
          strokeDasharray={circumference}
          strokeDashoffset={offset}
          style={{ transition:'stroke-dashoffset 0.9s ease-out, stroke 0.3s' }}
        />
        {/* Score text */}
        <text
          x={cx} y={cy - 6}
          textAnchor="middle"
          fontFamily="'JetBrains Mono', monospace"
          fontWeight="600"
          fontSize="28"
          fill={color}
        >
          {score.toFixed(1)}
        </text>
        <text
          x={cx} y={cy + 10}
          textAnchor="middle"
          fontFamily="'JetBrains Mono', monospace"
          fontSize="11"
          fill="var(--text-secondary)"
        >
          / 10
        </text>
      </svg>
      {label && (
        <div style={{
          fontFamily:'var(--font-mono)', fontSize:10,
          color:'var(--text-secondary)', letterSpacing:2,
          marginTop:-4,
        }}>
          {label}
        </div>
      )}
    </div>
  )
}
