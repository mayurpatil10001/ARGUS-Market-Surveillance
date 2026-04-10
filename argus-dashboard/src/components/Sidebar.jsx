import { useState } from 'react'
import { NavLink, useLocation } from 'react-router-dom'
import { useQuery } from 'react-query'
import { api } from '../api/client'

// ─── Icons ───────────────────────────────────────────────────────────────────
function IconRadar() {
  return (
    <svg width="18" height="18" viewBox="0 0 18 18" fill="none">
      <circle cx="9" cy="9" r="7" stroke="currentColor" strokeWidth="1.2"/>
      <circle cx="9" cy="9" r="4" stroke="currentColor" strokeWidth="1.2"/>
      <line x1="9" y1="9" x2="9" y2="2.5" stroke="currentColor" strokeWidth="1.4" strokeLinecap="round"/>
      <line x1="9" y1="9" x2="13.5" y2="6" stroke="currentColor" strokeWidth="1.4" strokeLinecap="round" opacity="0.4"/>
    </svg>
  )
}
function IconDNA() {
  return (
    <svg width="18" height="18" viewBox="0 0 18 18" fill="none">
      <path d="M6 3 Q9 6 12 9 Q9 12 6 15" stroke="currentColor" strokeWidth="1.2" fill="none" strokeLinecap="round"/>
      <path d="M12 3 Q9 6 6 9 Q9 12 12 15" stroke="currentColor" strokeWidth="1.2" fill="none" strokeLinecap="round"/>
      <line x1="7.5" y1="6.2" x2="10.5" y2="6.2" stroke="currentColor" strokeWidth="1" opacity="0.6"/>
      <line x1="7.5" y1="9"   x2="10.5" y2="9"   stroke="currentColor" strokeWidth="1" opacity="0.6"/>
      <line x1="7.5" y1="11.8" x2="10.5" y2="11.8" stroke="currentColor" strokeWidth="1" opacity="0.6"/>
    </svg>
  )
}
function IconNetwork() {
  return (
    <svg width="18" height="18" viewBox="0 0 18 18" fill="none">
      <circle cx="9" cy="9"  r="2"   fill="currentColor"/>
      <circle cx="3" cy="4"  r="1.5" stroke="currentColor" strokeWidth="1"/>
      <circle cx="15" cy="4" r="1.5" stroke="currentColor" strokeWidth="1"/>
      <circle cx="3" cy="14" r="1.5" stroke="currentColor" strokeWidth="1"/>
      <circle cx="15" cy="14" r="1.5" stroke="currentColor" strokeWidth="1"/>
      <line x1="7.2" y1="7.5" x2="4.3" y2="5.3"  stroke="currentColor" strokeWidth="1"/>
      <line x1="10.8" y1="7.5" x2="13.7" y2="5.3" stroke="currentColor" strokeWidth="1"/>
      <line x1="7.2" y1="10.5" x2="4.3" y2="12.7" stroke="currentColor" strokeWidth="1"/>
      <line x1="10.8" y1="10.5" x2="13.7" y2="12.7" stroke="currentColor" strokeWidth="1"/>
    </svg>
  )
}
function IconCase() {
  return (
    <svg width="18" height="18" viewBox="0 0 18 18" fill="none">
      <rect x="2" y="3" width="14" height="13" rx="2" stroke="currentColor" strokeWidth="1.2"/>
      <line x1="5.5" y1="7.5"  x2="12.5" y2="7.5"  stroke="currentColor" strokeWidth="1"/>
      <line x1="5.5" y1="10"   x2="12.5" y2="10"   stroke="currentColor" strokeWidth="1"/>
      <line x1="5.5" y1="12.5" x2="9"    y2="12.5" stroke="currentColor" strokeWidth="1"/>
    </svg>
  )
}
function IconChart() {
  return (
    <svg width="18" height="18" viewBox="0 0 18 18" fill="none">
      <rect x="2"   y="11" width="3.5" height="5" rx="1" fill="currentColor" opacity="0.65"/>
      <rect x="7.5" y="6"  width="3.5" height="10" rx="1" fill="currentColor" opacity="0.8"/>
      <rect x="13"  y="2"  width="3.5" height="14" rx="1" fill="currentColor"/>
    </svg>
  )
}
function IconShield() {
  return (
    <svg width="18" height="18" viewBox="0 0 18 18" fill="none">
      <path d="M9 2.5L3.5 5V9.5C3.5 13 6.5 15.5 9 16.5C11.5 15.5 14.5 13 14.5 9.5V5L9 2.5Z"
        stroke="currentColor" strokeWidth="1.2" fill="none"/>
      <path d="M6.5 9.5L8 11L11.5 7"
        stroke="currentColor" strokeWidth="1.4" strokeLinecap="round" strokeLinejoin="round"/>
    </svg>
  )
}
function IconBolt() {
  return (
    <svg width="18" height="18" viewBox="0 0 18 18" fill="none">
      <path d="M10.5 2.5L4 10H9L7.5 15.5L14 8H9L10.5 2.5Z"
        stroke="currentColor" strokeWidth="1.3" fill="none"
        strokeLinecap="round" strokeLinejoin="round"/>
    </svg>
  )
}
function IconChevronLeft() {
  return (
    <svg width="14" height="14" viewBox="0 0 14 14" fill="none">
      <path d="M9 11L5 7L9 3" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round"/>
    </svg>
  )
}
function IconChevronRight() {
  return (
    <svg width="14" height="14" viewBox="0 0 14 14" fill="none">
      <path d="M5 3L9 7L5 11" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round"/>
    </svg>
  )
}

const NAV = [
  { to: '/alerts',     label: 'Live Alerts',       icon: <IconRadar /> },
  { to: '/dna',        label: 'Account DNA',        icon: <IconDNA /> },
  { to: '/network',    label: 'Network Graph',      icon: <IconNetwork /> },
  { to: '/cases',      label: 'Case Builder',       icon: <IconCase /> },
  { to: '/summary',    label: 'Weekly Summary',     icon: <IconChart /> },
  { to: '/ps402',      label: 'Digital Threats',    icon: <IconBolt /> },
  { to: '/mitigation', label: 'Mitigation Center',  icon: <IconShield /> },
]

// ─── Status dot ───────────────────────────────────────────────────────────────
function StatusDot({ label, status, collapsed }) {
  const color =
    status === 'ok'             ? '#22d3ee' :
    status === 'not_configured' ? '#f59e0b' :
    status === 'unknown'        ? '#71717a' :
    '#ef4444'
  const glow = status === 'ok' ? `0 0 5px ${color}60` : 'none'

  return (
    <div title={collapsed ? `${label}: ${status}` : undefined}
      style={{
        display: 'flex', alignItems: 'center', gap: 7,
        marginBottom: 5, cursor: collapsed ? 'help' : 'default',
      }}>
      <div style={{
        width: 7, height: 7, borderRadius: '50%', flexShrink: 0,
        background: color, boxShadow: glow,
      }} />
      {!collapsed && (
        <span style={{
          fontSize: 9, color: 'var(--text-dim)',
          fontFamily: 'var(--font-mono)', letterSpacing: 1.5,
        }}>
          {label}
        </span>
      )}
    </div>
  )
}

// ─── Sidebar ──────────────────────────────────────────────────────────────────
export default function Sidebar() {
  const [collapsed, setCollapsed] = useState(false)
  const location = useLocation()
  const W = collapsed ? 60 : 240

  const { data: health } = useQuery('health', () => api.health(), {
    refetchInterval: 15000,
    select: r => r.data,
  })

  const dbStatus     = health?.database?.status || 'unknown'
  const redisStatus  = health?.redis?.status    || 'unknown'
  const gnnStatus    = health?.models?.gnn?.loaded       ? 'ok' : health?.models ? 'error' : 'unknown'
  const dnaStatus    = health?.models?.dna?.loaded       ? 'ok' : health?.models ? 'error' : 'unknown'
  const crossStatus  = health?.models?.cross_market?.loaded ? 'ok' : health?.models ? 'error' : 'unknown'
  const zdStatus     = health?.models?.zero_day?.loaded  ? 'ok' : health?.models ? 'error' : 'unknown'

  return (
    <aside style={{
      width: W,
      minWidth: W,
      background: 'var(--bg-card)',
      borderRight: '1px solid var(--border)',
      display: 'flex',
      flexDirection: 'column',
      flexShrink: 0,
      height: '100vh',
      position: 'sticky',
      top: 0,
      transition: 'width 0.2s ease, min-width 0.2s ease',
      overflow: 'hidden',
    }}>

      {/* ── Logo ────────────────────────────────────────────────────── */}
      <div style={{
        padding: collapsed ? '18px 0' : '18px 18px 0',
        display: 'flex',
        alignItems: 'center',
        justifyContent: collapsed ? 'center' : 'space-between',
        gap: 10,
      }}>
        {!collapsed && (
          <div>
            <div style={{
              fontFamily: 'var(--font-display)',
              fontWeight: 800,
              fontSize: 20,
              color: 'var(--accent-green)',
              letterSpacing: 5,
            }}>SENTINEL</div>
            <div style={{
              fontSize: 8,
              color: 'var(--text-dim)',
              fontFamily: 'var(--font-mono)',
              letterSpacing: 2,
              marginTop: 2,
            }}>THREAT DETECTION v2.0</div>
          </div>
        )}
        {collapsed && (
          <div style={{
            fontFamily: 'var(--font-display)',
            fontWeight: 900,
            fontSize: 16,
            color: 'var(--accent-green)',
            letterSpacing: 2,
          }}>S</div>
        )}
      </div>

      {/* ── Divider ─────────────────────────────────────────────────── */}
      <div style={{ height: 1, background: 'var(--border)', margin: '14px 0' }} />

      {/* ── Navigation ──────────────────────────────────────────────── */}
      <nav style={{ flex: 1 }}>
        {NAV.map(({ to, label, icon }) => {
          const active = location.pathname === to ||
            (to === '/alerts' && location.pathname === '/')
          return (
            <NavLink
              key={to}
              to={to}
              title={collapsed ? label : undefined}
              style={{
                display: 'flex',
                alignItems: 'center',
                justifyContent: collapsed ? 'center' : 'flex-start',
                gap: 10,
                padding: collapsed ? '0 0' : '0 16px',
                height: 44,
                color: active ? 'var(--accent-green)' : 'var(--text-secondary)',
                background: active ? 'rgba(34,211,238,0.06)' : 'transparent',
                borderLeft: active ? '2px solid var(--accent-green)' : '2px solid transparent',
                textDecoration: 'none',
                fontFamily: 'var(--font-mono)',
                fontSize: 11,
                letterSpacing: 0.5,
                transition: 'all 0.15s',
                cursor: 'pointer',
                userSelect: 'none',
              }}
              onMouseEnter={e => {
                if (!active) {
                  e.currentTarget.style.color = 'var(--text-primary)'
                  e.currentTarget.style.background = 'rgba(255,255,255,0.03)'
                }
              }}
              onMouseLeave={e => {
                if (!active) {
                  e.currentTarget.style.color = 'var(--text-secondary)'
                  e.currentTarget.style.background = 'transparent'
                }
              }}
            >
              <span style={{ opacity: active ? 1 : 0.55, flexShrink: 0 }}>{icon}</span>
              {!collapsed && label}
            </NavLink>
          )
        })}
      </nav>

      {/* ── Status section ──────────────────────────────────────────── */}
      <div style={{
        padding: collapsed ? '14px 0' : '14px 16px',
        borderTop: '1px solid var(--border)',
        display: 'flex',
        flexDirection: 'column',
        alignItems: collapsed ? 'center' : 'flex-start',
      }}>
        {!collapsed && (
          <div style={{
            fontSize: 8, color: 'var(--text-dim)',
            letterSpacing: 2, marginBottom: 8, fontFamily: 'var(--font-mono)',
          }}>
            SYSTEM STATUS
          </div>
        )}
        <StatusDot label="API"       status={health ? 'ok' : 'unknown'} collapsed={collapsed} />
        <StatusDot label="DATABASE"  status={dbStatus}    collapsed={collapsed} />
        <StatusDot label="REDIS"     status={redisStatus} collapsed={collapsed} />

        {!collapsed && (
          <div style={{
            fontSize: 8, color: 'var(--text-dim)',
            letterSpacing: 2, margin: '8px 0', fontFamily: 'var(--font-mono)',
          }}>
            AI ENGINES
          </div>
        )}
        {collapsed && <div style={{ height: 6 }} />}
        <StatusDot label="COORD DETECT" status={gnnStatus}   collapsed={collapsed} />
        <StatusDot label="BEHAV PROF"  status={dnaStatus}   collapsed={collapsed} />
        <StatusDot label="CROSS-PLAT"  status={crossStatus} collapsed={collapsed} />
        <StatusDot label="NOVEL THRT"  status={zdStatus}    collapsed={collapsed} />
      </div>

      {/* ── Collapse toggle ─────────────────────────────────────────── */}
      <button
        onClick={() => setCollapsed(c => !c)}
        style={{
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'center',
          height: 40,
          background: 'transparent',
          border: 'none',
          borderTop: '1px solid var(--border)',
          color: 'var(--text-dim)',
          cursor: 'pointer',
          gap: 6,
          fontFamily: 'var(--font-mono)',
          fontSize: 9,
          letterSpacing: 1.5,
          transition: 'color 0.15s',
        }}
        onMouseEnter={e => e.currentTarget.style.color = 'var(--text-primary)'}
        onMouseLeave={e => e.currentTarget.style.color = 'var(--text-dim)'}
      >
        {collapsed ? <IconChevronRight /> : <><IconChevronLeft /><span>COLLAPSE</span></>}
      </button>
    </aside>
  )
}
