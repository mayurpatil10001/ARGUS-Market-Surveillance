const SCHEME_CONFIG = {
  pump_and_dump:    { label:'PUMP & DUMP',  bg:'rgba(255,51,85,0.12)',  border:'rgba(255,51,85,0.4)',  color:'#ff3355' },
  spoofing:         { label:'SPOOFING',     bg:'rgba(255,179,0,0.12)', border:'rgba(255,179,0,0.4)', color:'#ffb300' },
  circular_trading: { label:'CIRCULAR',     bg:'rgba(124,58,237,0.12)',border:'rgba(124,58,237,0.4)',color:'#a78bfa' },
  insider_trading:  { label:'INSIDER',      bg:'rgba(59,130,246,0.12)',border:'rgba(59,130,246,0.4)',color:'#60a5fa' },
  zero_day:         { label:'ZERO-DAY',     bg:'rgba(0,255,136,0.12)', border:'rgba(0,255,136,0.4)', color:'#00ff88' },
}

export default function SchemeBadge({ type }) {
  const cfg = SCHEME_CONFIG[type] || SCHEME_CONFIG.zero_day
  return (
    <span style={{
      fontFamily: 'var(--font-mono)',
      fontSize: 9,
      fontWeight: 600,
      letterSpacing: 1.5,
      textTransform: 'uppercase',
      color: cfg.color,
      background: cfg.bg,
      border: `1px solid ${cfg.border}`,
      padding: '2px 6px',
      whiteSpace: 'nowrap',
    }}>
      {cfg.label}
    </span>
  )
}
