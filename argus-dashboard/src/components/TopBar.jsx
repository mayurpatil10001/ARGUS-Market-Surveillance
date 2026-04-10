import { useState, useEffect } from 'react'
import { useLocation } from 'react-router-dom'
import { useQuery } from 'react-query'
import { api } from '../api/client'

const PAGE_LABELS = {
  '/alerts':  'Live Alerts',
  '/dna':     'Account DNA',
  '/network': 'Network Graph',
  '/cases':   'Case Builder',
  '/summary': 'Weekly Summary',
}

function isMarketOpen() {
  const ist = new Date(new Date().toLocaleString('en-US', { timeZone: 'Asia/Kolkata' }))
  const h = ist.getHours(), m = ist.getMinutes()
  const totalMins = h * 60 + m
  return totalMins >= 9 * 60 + 15 && totalMins <= 15 * 60 + 30
}

export default function TopBar() {
  const location = useLocation()
  const [clock, setClock] = useState('')
  const [live, setLive] = useState(false)

  const { data: alertData } = useQuery('alerts_count', () => api.getAlerts({ status:'open' }), {
    refetchInterval: 30000,
    select: r => r.data,
  })

  useEffect(() => {
    const update = () => {
      const ist = new Date(new Date().toLocaleString('en-US', { timeZone: 'Asia/Kolkata' }))
      const pad = n => String(n).padStart(2,'0')
      setClock(`IST ${pad(ist.getHours())}:${pad(ist.getMinutes())}:${pad(ist.getSeconds())}`)
      setLive(isMarketOpen())
    }
    update()
    const id = setInterval(update, 1000)
    return () => clearInterval(id)
  }, [])

  const pageLabel = PAGE_LABELS[location.pathname] || 'Dashboard'
  const alertCount = alertData?.total || 0

  return (
    <header style={{
      height: 48,
      background: 'var(--bg-card)',
      borderBottom: '1px solid var(--border)',
      display: 'flex',
      alignItems: 'center',
      padding: '0 24px',
      gap: 16,
      flexShrink: 0,
      zIndex: 100,
    }}>
      {/* Breadcrumb */}
      <div style={{ fontFamily:'var(--font-mono)', fontSize:12, color:'var(--text-secondary)', flex:1 }}>
        <span style={{ color:'var(--text-dim)' }}>ARGUS</span>
        <span style={{ margin:'0 6px', color:'var(--text-dim)' }}>/</span>
        <span style={{ color:'var(--text-primary)' }}>{pageLabel.toUpperCase()}</span>
      </div>

      {/* Clock */}
      <div style={{
        fontFamily: 'var(--font-mono)',
        fontSize: 13,
        color: 'var(--text-primary)',
        fontWeight: 500,
        letterSpacing: 1,
      }}>
        {clock}
      </div>

      {/* Live / Closed badge */}
      <div style={{
        display: 'flex',
        alignItems: 'center',
        gap: 6,
        padding: '3px 10px',
        border: `1px solid ${live ? 'rgba(0,255,136,0.3)' : 'rgba(255,179,0,0.3)'}`,
        background: live ? 'rgba(0,255,136,0.06)' : 'rgba(255,179,0,0.06)',
      }}>
        <div
          className={live ? 'live-pulse' : ''}
          style={{
            width: 6, height: 6,
            borderRadius: '50%',
            background: live ? 'var(--accent-green)' : 'var(--accent-amber)',
          }}
        />
        <span style={{
          fontFamily: 'var(--font-mono)',
          fontSize: 10,
          color: live ? 'var(--accent-green)' : 'var(--accent-amber)',
          letterSpacing: 1,
        }}>
          {live ? 'LIVE' : 'CLOSED'}
        </span>
      </div>

      {/* Alert count */}
      {alertCount > 0 && (
        <div style={{
          padding: '3px 10px',
          background: 'rgba(255,51,85,0.15)',
          border: '1px solid rgba(255,51,85,0.3)',
          color: 'var(--accent-red)',
          fontFamily: 'var(--font-mono)',
          fontSize: 10,
          fontWeight: 600,
          letterSpacing: 1,
        }}>
          {alertCount} ALERTS
        </div>
      )}

      {/* Analyst label */}
      <div style={{
        fontFamily: 'var(--font-mono)',
        fontSize: 10,
        color: 'var(--text-dim)',
        letterSpacing: 1,
        borderLeft: '1px solid var(--border)',
        paddingLeft: 16,
      }}>
        SEBI ANALYST
      </div>
    </header>
  )
}
