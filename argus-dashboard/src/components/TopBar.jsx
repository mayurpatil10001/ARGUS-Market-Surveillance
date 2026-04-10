import { useState, useEffect } from 'react'
import { useLocation } from 'react-router-dom'
import { useQuery } from 'react-query'
import { api } from '../api/client'

const PAGE_LABELS = {
  '/alerts':     'Live Alerts',
  '/dna':        'Account DNA',
  '/network':    'Network Graph',
  '/cases':      'Case Builder',
  '/summary':    'Weekly Summary',
  '/mitigation': 'Mitigation Center',
}

export default function TopBar() {
  const location = useLocation()
  const [clock, setClock] = useState('')
  const [marketOpen, setMarketOpen] = useState(false)

  // Alert count badge
  const { data: alertData } = useQuery(
    'topbar_alert_count',
    () => api.getAlerts({ status: 'open', limit: 1 }),
    { refetchInterval: 30000, select: r => r.data }
  )

  useEffect(() => {
    const tick = () => {
      const now = new Date()
      const pad = n => String(n).padStart(2, '0')
      // UTC clock
      setClock(`${pad(now.getUTCHours())}:${pad(now.getUTCMinutes())}:${pad(now.getUTCSeconds())} UTC`)

      // IST market hours: 09:15–15:30
      const ist = new Date(now.toLocaleString('en-US', { timeZone: 'Asia/Kolkata' }))
      const mins = ist.getHours() * 60 + ist.getMinutes()
      setMarketOpen(mins >= 9 * 60 + 15 && mins <= 15 * 60 + 30)
    }
    tick()
    const id = setInterval(tick, 1000)
    return () => clearInterval(id)
  }, [])

  const pageLabel  = PAGE_LABELS[location.pathname] || 'Dashboard'
  const alertCount = alertData?.total ?? alertData?.alerts?.length ?? 0

  return (
    <header style={{
      height: 50,
      background: 'var(--bg-card)',
      borderBottom: '1px solid var(--border)',
      display: 'flex',
      alignItems: 'center',
      padding: '0 20px',
      gap: 16,
      flexShrink: 0,
      zIndex: 100,
    }}>

      {/* ── ARGUS LIVE badge ─────────────────────────────────────────── */}
      <div style={{
        display: 'flex',
        alignItems: 'center',
        gap: 7,
        padding: '4px 10px',
        border: `1px solid ${marketOpen ? 'rgba(34,211,238,0.35)' : 'var(--border)'}`,
        borderRadius: 6,
        background: marketOpen ? 'rgba(34,211,238,0.06)' : 'transparent',
      }}>
        <div
          className={marketOpen ? 'live-pulse' : ''}
          style={{
            width: 7, height: 7, borderRadius: '50%',
            background: marketOpen ? 'var(--accent-green)' : 'var(--text-dim)',
            flexShrink: 0,
          }}
        />
        <span style={{
          fontFamily: 'var(--font-mono)',
          fontSize: 10,
          fontWeight: 700,
          color: marketOpen ? 'var(--accent-green)' : 'var(--text-dim)',
          letterSpacing: 1.5,
        }}>
          {marketOpen ? 'SENTINEL LIVE' : 'MONITORING PAUSED'}
        </span>
      </div>

      {/* ── Breadcrumb ───────────────────────────────────────────────── */}
      <div style={{
        fontFamily: 'var(--font-mono)',
        fontSize: 11,
        color: 'var(--text-secondary)',
        flex: 1,
      }}>
        <span style={{ color: 'var(--text-dim)' }}>SENTINEL</span>
        <span style={{ margin: '0 5px', color: 'var(--border-bright)' }}>/</span>
        <span style={{ color: 'var(--text-primary)', fontWeight: 600 }}>
          {pageLabel.toUpperCase()}
        </span>
      </div>

      {/* ── UTC Clock ────────────────────────────────────────────────── */}
      <div style={{
        fontFamily: 'var(--font-mono)',
        fontSize: 12,
        color: 'var(--text-secondary)',
        letterSpacing: 1,
        fontVariantNumeric: 'tabular-nums',
      }}>
        {clock}
      </div>

      {/* ── Open alert count badge ───────────────────────────────────── */}
      {alertCount > 0 && (
        <div style={{
          display: 'flex',
          alignItems: 'center',
          gap: 6,
          padding: '4px 10px',
          background: 'rgba(239,68,68,0.12)',
          border: '1px solid rgba(239,68,68,0.35)',
          borderRadius: 6,
        }}>
          <div style={{
            width: 6, height: 6, borderRadius: '50%',
            background: 'var(--accent-red)',
          }} className="live-pulse" />
          <span style={{
            fontFamily: 'var(--font-mono)',
            fontSize: 10,
            fontWeight: 700,
            color: 'var(--accent-red)',
            letterSpacing: 1,
          }}>
            {alertCount} {alertCount === 1 ? 'ALERT' : 'ALERTS'}
          </span>
        </div>
      )}

      {/* ── Analyst label ────────────────────────────────────────────── */}
      <div style={{
        fontFamily: 'var(--font-mono)',
        fontSize: 10,
        color: 'var(--text-dim)',
        letterSpacing: 1,
        paddingLeft: 14,
        borderLeft: '1px solid var(--border)',
      }}>
        THREAT ANALYST
      </div>
    </header>
  )
}
