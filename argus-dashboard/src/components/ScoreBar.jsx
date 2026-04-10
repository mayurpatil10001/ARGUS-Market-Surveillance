import { useEffect, useRef, useState } from 'react'

function scoreColor(score) {
  if (score >= 8) return 'var(--accent-red)'
  if (score >= 6) return 'var(--accent-amber)'
  return 'var(--accent-green)'
}

export default function ScoreBar({ label, score, weight }) {
  const [width, setWidth] = useState(0)
  const pct = (score / 10) * 100

  useEffect(() => {
    const t = setTimeout(() => setWidth(pct), 80)
    return () => clearTimeout(t)
  }, [pct])

  const color = scoreColor(score)
  const filled = Math.round(score)
  const empty  = 10 - filled
  const barStr = '█'.repeat(filled) + '░'.repeat(empty)

  return (
    <div style={{ marginBottom: 10 }}>
      <div style={{ display:'flex', alignItems:'center', gap:8, marginBottom:4 }}>
        <span style={{
          fontFamily: 'var(--font-mono)', fontSize:11,
          color:'var(--text-secondary)', width:160, flexShrink:0,
        }}>
          {label}
        </span>
        <div style={{
          flex:1, height:4,
          background:'var(--border-bright)',
          position:'relative', overflow:'hidden',
        }}>
          <div style={{
            position:'absolute', left:0, top:0, bottom:0,
            background: color,
            width: `${width}%`,
            transition: 'width 0.8s ease-out',
            boxShadow: `0 0 8px ${color}40`,
          }} />
        </div>
        <span style={{
          fontFamily:'var(--font-mono)', fontSize:11,
          color, width:40, textAlign:'right', flexShrink:0,
        }}>
          {score.toFixed(1)}/10
        </span>
        {weight && (
          <span style={{
            fontFamily:'var(--font-mono)', fontSize:10,
            color:'var(--text-dim)', width:42, flexShrink:0,
          }}>
            {weight}%
          </span>
        )}
      </div>
    </div>
  )
}
