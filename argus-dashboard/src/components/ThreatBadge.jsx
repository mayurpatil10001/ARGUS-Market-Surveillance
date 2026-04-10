const THREAT_CONFIG = {
  coordinated_attack: { label: 'COORD ATTACK',    bg: 'rgba(255,51,51,0.12)',   border: 'rgba(255,51,51,0.4)',   color: '#ff3333' },
  malicious_content:  { label: 'MALICIOUS',        bg: 'rgba(255,140,0,0.12)',   border: 'rgba(255,140,0,0.4)',   color: '#ff8c00' },
  phishing:           { label: 'PHISHING',          bg: 'rgba(255,230,0,0.12)',   border: 'rgba(255,230,0,0.4)',   color: '#ffe600' },
  misinformation:     { label: 'MISINFO',           bg: 'rgba(160,0,255,0.12)',   border: 'rgba(160,0,255,0.4)',   color: '#a000ff' },
  platform_abuse:     { label: 'PLATFORM ABUSE',   bg: 'rgba(59,130,246,0.12)',  border: 'rgba(59,130,246,0.4)',  color: '#3b82f6' },
  novel_threat:       { label: 'NOVEL THREAT',     bg: 'rgba(0,255,255,0.12)',   border: 'rgba(0,255,255,0.4)',   color: '#00ffff' },
  // Legacy scheme type aliases — mapped to PS-402 categories
  pump_and_dump:      { label: 'COORD ATTACK',     bg: 'rgba(255,51,51,0.12)',   border: 'rgba(255,51,51,0.4)',   color: '#ff3333' },
  circular_trading:   { label: 'MALICIOUS',        bg: 'rgba(255,140,0,0.12)',   border: 'rgba(255,140,0,0.4)',   color: '#ff8c00' },
  spoofing:           { label: 'PHISHING',          bg: 'rgba(255,230,0,0.12)',   border: 'rgba(255,230,0,0.4)',   color: '#ffe600' },
  insider_trading:    { label: 'PLATFORM ABUSE',   bg: 'rgba(59,130,246,0.12)',  border: 'rgba(59,130,246,0.4)',  color: '#3b82f6' },
  zero_day_anomaly:   { label: 'NOVEL THREAT',     bg: 'rgba(0,255,255,0.12)',   border: 'rgba(0,255,255,0.4)',   color: '#00ffff' },
}

/**
 * ThreatBadge — PS-402 threat category badge component.
 * Replaces SchemeBadge with new threat-detection categories and colors.
 * Backward compatible: accepts both new threat_category and legacy scheme_type values.
 */
export default function ThreatBadge({ type, category }) {
  const key = category || type || 'novel_threat'
  const cfg = THREAT_CONFIG[key] || THREAT_CONFIG.novel_threat
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

// Backward-compatible alias
export { ThreatBadge as SchemeBadge }
