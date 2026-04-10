import { NavLink, useLocation } from 'react-router-dom'
import { useQuery } from 'react-query'
import { api } from '../api/client'

const NAV = [
  { to:'/alerts',  label:'Live Alerts',    icon: <IconRadar /> },
  { to:'/dna',     label:'Account DNA',    icon: <IconDNA /> },
  { to:'/network', label:'Network Graph',  icon: <IconNetwork /> },
  { to:'/cases',   label:'Case Builder',   icon: <IconCase /> },
  { to:'/summary', label:'Weekly Summary', icon: <IconChart /> },
]

function IconRadar() {
  return (
    <svg width="16" height="16" viewBox="0 0 16 16" fill="none">
      <circle cx="8" cy="8" r="6.5" stroke="currentColor" strokeWidth="1"/>
      <circle cx="8" cy="8" r="3.5" stroke="currentColor" strokeWidth="1"/>
      <line x1="8" y1="8" x2="8" y2="2" stroke="currentColor" strokeWidth="1.2" strokeLinecap="round"/>
      <line x1="8" y1="8" x2="12.5" y2="5.3" stroke="currentColor" strokeWidth="1.2" strokeLinecap="round" opacity="0.4"/>
    </svg>
  )
}
function IconDNA() {
  return (
    <svg width="16" height="16" viewBox="0 0 16 16" fill="none">
      <ellipse cx="8" cy="8" rx="5" ry="2.5" stroke="currentColor" strokeWidth="1"/>
      <ellipse cx="8" cy="8" rx="2.5" ry="5" stroke="currentColor" strokeWidth="1"/>
      <circle cx="8" cy="3" r="1" fill="currentColor"/>
      <circle cx="8" cy="13" r="1" fill="currentColor"/>
    </svg>
  )
}
function IconNetwork() {
  return (
    <svg width="16" height="16" viewBox="0 0 16 16" fill="none">
      <circle cx="8" cy="8" r="2" fill="currentColor"/>
      <circle cx="3" cy="4" r="1.5" stroke="currentColor" strokeWidth="1"/>
      <circle cx="13" cy="4" r="1.5" stroke="currentColor" strokeWidth="1"/>
      <circle cx="3" cy="12" r="1.5" stroke="currentColor" strokeWidth="1"/>
      <circle cx="13" cy="12" r="1.5" stroke="currentColor" strokeWidth="1"/>
      <line x1="6.2" y1="6.8" x2="4.2" y2="5.2" stroke="currentColor" strokeWidth="1"/>
      <line x1="9.8" y1="6.8" x2="11.8" y2="5.2" stroke="currentColor" strokeWidth="1"/>
      <line x1="6.2" y1="9.2" x2="4.2" y2="10.8" stroke="currentColor" strokeWidth="1"/>
      <line x1="9.8" y1="9.2" x2="11.8" y2="10.8" stroke="currentColor" strokeWidth="1"/>
    </svg>
  )
}
function IconCase() {
  return (
    <svg width="16" height="16" viewBox="0 0 16 16" fill="none">
      <rect x="2.5" y="2.5" width="11" height="11" rx="0" stroke="currentColor" strokeWidth="1"/>
      <line x1="5" y1="6" x2="11" y2="6" stroke="currentColor" strokeWidth="1"/>
      <line x1="5" y1="8.5" x2="11" y2="8.5" stroke="currentColor" strokeWidth="1"/>
      <line x1="5" y1="11" x2="8" y2="11" stroke="currentColor" strokeWidth="1"/>
    </svg>
  )
}
function IconChart() {
  return (
    <svg width="16" height="16" viewBox="0 0 16 16" fill="none">
      <rect x="2" y="9" width="3" height="5" fill="currentColor" opacity="0.7"/>
      <rect x="6.5" y="5" width="3" height="9" fill="currentColor" opacity="0.85"/>
      <rect x="11" y="2" width="3" height="12" fill="currentColor"/>
    </svg>
  )
}

function StatusDot({ label, status }) {
  const color = status === 'ok' ? 'var(--accent-green)'
              : status === 'not_configured' ? 'var(--accent-amber)'
              : 'var(--accent-red)'
  return (
    <div style={{ display:'flex', alignItems:'center', gap:6, marginBottom:4 }}>
      <div style={{ width:7, height:7, borderRadius:'50%', background:color, flexShrink:0,
        boxShadow: status === 'ok' ? `0 0 6px ${color}` : 'none' }} />
      <span style={{ fontSize:10, color:'var(--text-secondary)', fontFamily:'var(--font-mono)' }}>
        {label}
      </span>
    </div>
  )
}

export default function Sidebar() {
  const location = useLocation()

  const { data: health } = useQuery('health', () => api.health(), {
    refetchInterval: 10000,
    select: r => r.data,
  })

  const dbStatus     = health?.database?.status || 'unknown'
  const redisStatus  = health?.redis?.status || 'unknown'
  const modelStatus  = health?.models?.gnn?.loaded ? 'ok' : 'error'

  return (
    <aside style={{
      width: 220,
      background: 'var(--bg-card)',
      borderRight: '1px solid var(--border)',
      display: 'flex',
      flexDirection: 'column',
      flexShrink: 0,
      height: '100vh',
      position: 'sticky',
      top: 0,
    }}>
      {/* Logo */}
      <div style={{ padding:'20px 20px 0' }}>
        <div style={{
          fontFamily: 'var(--font-display)',
          fontWeight: 800,
          fontSize: 22,
          color: 'var(--accent-green)',
          letterSpacing: 4,
          textShadow: '0 0 20px rgba(0,255,136,0.4)',
        }}>ARGUS</div>
        <div style={{
          fontSize: 9,
          color: 'var(--text-dim)',
          fontFamily: 'var(--font-mono)',
          letterSpacing: 2,
          marginTop: 2,
        }}>SURVEILLANCE SYSTEM v1.0</div>
      </div>

      <div style={{ height:1, background:'var(--border)', margin:'16px 0' }} />

      {/* Navigation */}
      <nav style={{ flex:1 }}>
        {NAV.map(({ to, label, icon }) => {
          const active = location.pathname === to ||
            (to === '/alerts' && location.pathname === '/')
          return (
            <NavLink
              key={to}
              to={to}
              style={{
                display: 'flex',
                alignItems: 'center',
                gap: 10,
                padding: '0 16px',
                height: 40,
                color: active ? 'var(--accent-green)' : 'var(--text-secondary)',
                background: active ? 'var(--bg-surface)' : 'transparent',
                borderLeft: active ? '2px solid var(--accent-green)' : '2px solid transparent',
                textDecoration: 'none',
                fontFamily: 'var(--font-mono)',
                fontSize: 12,
                letterSpacing: 0.5,
                transition: 'all 0.15s ease-out',
                cursor: 'pointer',
              }}
              onMouseEnter={e => {
                if (!active) {
                  e.currentTarget.style.color = 'var(--text-primary)'
                  e.currentTarget.style.background = 'var(--bg-surface)'
                }
              }}
              onMouseLeave={e => {
                if (!active) {
                  e.currentTarget.style.color = 'var(--text-secondary)'
                  e.currentTarget.style.background = 'transparent'
                }
              }}
            >
              <span style={{ opacity: active ? 1 : 0.6 }}>{icon}</span>
              {label}
            </NavLink>
          )
        })}
      </nav>

      {/* Status indicators */}
      <div style={{
        padding: '16px 20px',
        borderTop: '1px solid var(--border)',
      }}>
        <div style={{ fontSize:9, color:'var(--text-dim)', letterSpacing:2, marginBottom:8 }}>
          SYSTEM STATUS
        </div>
        <StatusDot label="API" status={health ? 'ok' : 'error'} />
        <StatusDot label="DATABASE" status={dbStatus} />
        <StatusDot label="REDIS" status={redisStatus} />
        <StatusDot label="MODELS" status={modelStatus} />
      </div>
    </aside>
  )
}
