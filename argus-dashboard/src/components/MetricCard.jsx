import { useState, useEffect, useRef } from 'react'

export default function MetricCard({ label, value, unit = '', color = 'var(--accent-green)', delta, deltaLabel, style }) {
  const [display, setDisplay] = useState(0)
  const rafRef = useRef(null)
  const numeric = parseFloat(String(value).replace(/[^0-9.]/g,'')) || 0
  const isFloat  = String(value).includes('.')

  useEffect(() => {
    const start = performance.now()
    const duration = 1000
    const animate = (now) => {
      const t = Math.min((now - start) / duration, 1)
      const ease = 1 - Math.pow(1 - t, 3)
      const curr = numeric * ease
      setDisplay(isFloat ? parseFloat(curr.toFixed(1)) : Math.round(curr))
      if (t < 1) rafRef.current = requestAnimationFrame(animate)
    }
    rafRef.current = requestAnimationFrame(animate)
    return () => cancelAnimationFrame(rafRef.current)
  }, [numeric])

  const displayStr = isFloat ? display.toFixed(1) : String(display)

  return (
    <div style={{
      background: 'var(--bg-card)',
      border: '1px solid var(--border)',
      borderLeft: `2px solid ${color}`,
      padding: 20,
      position: 'relative',
      ...style,
    }}>
      <div style={{
        fontSize: 10,
        color: 'var(--text-secondary)',
        fontFamily: 'var(--font-mono)',
        letterSpacing: 2,
        textTransform: 'uppercase',
        marginBottom: 10,
      }}>
        {label}
      </div>

      <div style={{ display:'flex', alignItems:'baseline', gap:4 }}>
        <div className="number-reveal" style={{
          fontFamily: 'var(--font-mono)',
          fontWeight: 600,
          fontSize: 28,
          color,
          lineHeight: 1,
        }}>
          {displayStr}
        </div>
        {unit && (
          <div style={{ fontSize:13, color:'var(--text-secondary)', fontFamily:'var(--font-mono)' }}>
            {unit}
          </div>
        )}
      </div>

      {delta !== undefined && (
        <div style={{
          display: 'flex',
          alignItems: 'center',
          gap: 4,
          marginTop: 8,
          fontSize: 10,
          color: delta >= 0 ? 'var(--accent-green)' : 'var(--accent-red)',
        }}>
          <span>{delta >= 0 ? '▲' : '▼'}</span>
          <span style={{ fontFamily:'var(--font-mono)' }}>
            {Math.abs(delta)}{deltaLabel || ''}
          </span>
        </div>
      )}
    </div>
  )
}
