import { useState } from 'react'
import { useQuery } from 'react-query'
import { api } from '../api/client'
import MetricCard from '../components/MetricCard'
import ScoreBar from '../components/ScoreBar'

// ── Helpers ───────────────────────────────────────────────────────────────────
function fmt(dt) {
  if (!dt) return '—'
  try { return new Date(dt).toLocaleString('en-IN', { hour12: false }) }
  catch { return dt }
}

function ThreatScoreBar({ value }) {
  const color =
    value >= 0.8 ? '#ef4444' :
    value >= 0.5 ? '#f59e0b' :
    '#22d3ee'
  return (
    <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
      <div style={{
        flex: 1, height: 6, background: 'var(--border)',
        borderRadius: 3, overflow: 'hidden',
      }}>
        <div style={{
          width: `${Math.round(value * 100)}%`,
          height: '100%',
          background: color,
          transition: 'width 0.3s',
        }} />
      </div>
      <span style={{
        fontFamily: 'var(--font-mono)', fontSize: 11,
        color, minWidth: 36, textAlign: 'right',
      }}>
        {value.toFixed(3)}
      </span>
    </div>
  )
}

function TypeBadge({ type }) {
  const MAP = {
    url_threat:       { label: 'URL',       bg: '#7c3aed', fg: '#ede9fe' },
    social_post:      { label: 'SOCIAL',    bg: '#0369a1', fg: '#e0f2fe' },
    news_headline:    { label: 'NEWS',      bg: '#065f46', fg: '#d1fae5' },
    whatsapp_forward: { label: 'WHATSAPP',  bg: '#854d0e', fg: '#fef3c7' },
  }
  const style = MAP[type] || { label: type?.toUpperCase() || '?', bg: '#374151', fg: '#e5e7eb' }
  return (
    <span style={{
      background: style.bg, color: style.fg,
      fontFamily: 'var(--font-mono)', fontSize: 9,
      fontWeight: 700, letterSpacing: 1.2,
      padding: '2px 7px', borderRadius: 2,
    }}>
      {style.label}
    </span>
  )
}

function PlatformPill({ platform }) {
  return (
    <span style={{
      border: '1px solid var(--border-bright)',
      color: 'var(--text-secondary)',
      fontFamily: 'var(--font-mono)', fontSize: 9,
      padding: '1px 6px', borderRadius: 2, letterSpacing: 1,
    }}>
      {(platform || '?').toUpperCase()}
    </span>
  )
}

function MarketMovingBadge({ yes }) {
  return yes ? (
    <span style={{
      background: '#7f1d1d', color: '#fca5a5',
      fontFamily: 'var(--font-mono)', fontSize: 9,
      fontWeight: 700, padding: '2px 7px', borderRadius: 2,
      letterSpacing: 1,
    }}>⚡ YES</span>
  ) : (
    <span style={{
      color: 'var(--text-dim)',
      fontFamily: 'var(--font-mono)', fontSize: 9,
      padding: '2px 7px',
    }}>–</span>
  )
}

// ── Expandable Row ────────────────────────────────────────────────────────────
function SignalRow({ sig }) {
  const [open, setOpen] = useState(false)
  return (
    <>
      <tr
        onClick={() => setOpen(o => !o)}
        style={{
          cursor: 'pointer',
          background: open ? 'rgba(34,211,238,0.04)' : 'transparent',
          transition: 'background 0.15s',
        }}
        onMouseEnter={e => { if (!open) e.currentTarget.style.background = 'rgba(255,255,255,0.025)' }}
        onMouseLeave={e => { if (!open) e.currentTarget.style.background = 'transparent' }}
      >
        <td style={TD}>{fmt(sig.ingested_at)}</td>
        <td style={TD}><TypeBadge type={sig.signal_type} /></td>
        <td style={TD}><PlatformPill platform={sig.platform} /></td>
        <td style={TD}>
          {(sig.scrips_mentioned || []).slice(0, 3).map(s => (
            <span key={s} style={{
              background: 'rgba(34,211,238,0.12)',
              color: 'var(--accent-green)',
              fontFamily: 'var(--font-mono)', fontSize: 9,
              padding: '1px 5px', borderRadius: 2, marginRight: 3,
            }}>{s}</span>
          ))}
        </td>
        <td style={{ ...TD, width: 180 }}>
          <ThreatScoreBar value={sig.threat_score || 0} />
        </td>
        <td style={{ ...TD, fontFamily: 'var(--font-mono)', fontSize: 10, color: 'var(--text-secondary)' }}>
          {(sig.misinfo_score || 0).toFixed(3)}
        </td>
        <td style={{ ...TD, fontFamily: 'var(--font-mono)', fontSize: 10, color: 'var(--text-secondary)' }}>
          {(sig.social_signal_score || 0).toFixed(3)}
        </td>
        <td style={TD}><MarketMovingBadge yes={sig.is_market_moving} /></td>
        <td style={TD}>
          {sig.alert_id
            ? <span style={{ fontFamily: 'var(--font-mono)', fontSize: 9, color: '#f59e0b' }}>
                🔔 {sig.alert_id.slice(0, 8)}…
              </span>
            : <span style={{ color: 'var(--text-dim)', fontSize: 9 }}>—</span>
          }
        </td>
      </tr>
      {open && (
        <tr style={{ background: 'rgba(34,211,238,0.03)' }}>
          <td colSpan={9} style={{ padding: '12px 20px', borderBottom: '1px solid var(--border)' }}>
            <div style={{ display: 'flex', gap: 24, flexWrap: 'wrap' }}>
              {sig.source_url && (
                <div>
                  <div style={LABEL}>Source URL</div>
                  <a href={sig.source_url} target="_blank" rel="noreferrer"
                    style={{ fontFamily: 'var(--font-mono)', fontSize: 10, color: '#7c3aed', wordBreak: 'break-all' }}>
                    {sig.source_url}
                  </a>
                </div>
              )}
              {sig.raw_text_preview && (
                <div style={{ flex: 1 }}>
                  <div style={LABEL}>Text Preview</div>
                  <div style={{ fontFamily: 'var(--font-mono)', fontSize: 10, color: 'var(--text-secondary)', whiteSpace: 'pre-wrap' }}>
                    {sig.raw_text_preview}
                  </div>
                </div>
              )}
              <div>
                <div style={LABEL}>Signal ID</div>
                <span style={{ fontFamily: 'var(--font-mono)', fontSize: 9, color: 'var(--text-dim)' }}>{sig.id}</span>
              </div>
              {sig.alert_id && (
                <div>
                  <div style={LABEL}>Alert ID</div>
                  <span style={{ fontFamily: 'var(--font-mono)', fontSize: 9, color: '#f59e0b' }}>{sig.alert_id}</span>
                </div>
              )}
            </div>
          </td>
        </tr>
      )}
    </>
  )
}

// ── Styles ────────────────────────────────────────────────────────────────────
const TH = {
  padding: '8px 12px',
  textAlign: 'left',
  fontFamily: 'var(--font-mono)',
  fontSize: 9,
  letterSpacing: 1.5,
  color: 'var(--text-dim)',
  borderBottom: '1px solid var(--border)',
  whiteSpace: 'nowrap',
  userSelect: 'none',
}
const TD = {
  padding: '9px 12px',
  borderBottom: '1px solid var(--border)',
  verticalAlign: 'middle',
  fontSize: 11,
  color: 'var(--text-primary)',
}
const LABEL = {
  fontSize: 8,
  letterSpacing: 1.5,
  color: 'var(--text-dim)',
  fontFamily: 'var(--font-mono)',
  marginBottom: 4,
  textTransform: 'uppercase',
}

// ── Main Page ─────────────────────────────────────────────────────────────────
export default function PS402Signals() {
  const [scrip, setScrip]           = useState('')
  const [platform, setPlatform]     = useState('')
  const [mkMoving, setMkMoving]     = useState('')
  const [tick, setTick]             = useState(0)

  const filters = {
    ...(scrip    ? { scrip }              : {}),
    ...(platform ? { platform }           : {}),
    ...(mkMoving ? { is_market_moving: mkMoving === 'true' } : {}),
    limit: 100,
  }

  const { data: summary } = useQuery(
    ['ps402-summary', tick],
    () => api.get('/ps402/summary').then(r => r.data),
    { retry: 1, refetchInterval: 30000 },
  )

  const { data: sigData, isFetching } = useQuery(
    ['ps402-signals', filters, tick],
    () => api.get('/ps402/signals', { params: filters }).then(r => r.data),
    { retry: 1, refetchInterval: 30000 },
  )

  const signals = sigData?.signals || []

  return (
    <div style={{ color: 'var(--text-primary)' }}>
      {/* ── Header ─────────────────────────────────────────────────────── */}
      <div style={{ marginBottom: 24 }}>
        <div style={{ display: 'flex', alignItems: 'baseline', gap: 12 }}>
          <h1 style={{
            fontFamily: 'var(--font-display)', fontSize: 22, fontWeight: 700,
            color: 'var(--accent-green)', letterSpacing: 2, margin: 0,
          }}>
            PS-402 · DIGITAL THREATS
          </h1>
          {isFetching && (
            <span style={{ fontFamily: 'var(--font-mono)', fontSize: 9, color: 'var(--text-dim)', letterSpacing: 1.5 }}>
              REFRESHING…
            </span>
          )}
        </div>
        <div style={{ fontFamily: 'var(--font-mono)', fontSize: 10, color: 'var(--text-dim)', marginTop: 4, letterSpacing: 1 }}>
          URL phishing · social manipulation · WhatsApp fakes · news misinfo
        </div>
      </div>

      {/* ── Metric strip ───────────────────────────────────────────────── */}
      <div style={{ display: 'grid', gridTemplateColumns: 'repeat(5, 1fr)', gap: 12, marginBottom: 20 }}>
        <MetricCard label="Total Signals (7d)" value={summary?.total_signals ?? '—'} accent="var(--accent-green)" />
        <MetricCard label="Market-Moving"      value={summary?.market_moving  ?? '—'} accent="#ef4444" />
        <MetricCard label="Avg Threat Score"   value={summary?.avg_threat_score != null ? summary.avg_threat_score.toFixed(3) : '—'} accent="#f59e0b" />
        <MetricCard label="Phishing URLs"      value={summary?.by_type?.url_threat ?? 0} accent="#7c3aed" />
        <MetricCard label="Social Posts"       value={summary?.by_type?.social_post ?? 0} accent="#0369a1" />
      </div>

      {/* ── Filter bar ─────────────────────────────────────────────────── */}
      <div style={{
        display: 'flex', gap: 10, alignItems: 'center', flexWrap: 'wrap',
        marginBottom: 16,
        padding: '10px 14px',
        background: 'var(--bg-card)',
        border: '1px solid var(--border)',
        borderRadius: 4,
      }}>
        <select
          value={platform}
          onChange={e => setPlatform(e.target.value)}
          style={SELECT}
        >
          <option value="">All Platforms</option>
          {['web','twitter','reddit','telegram','whatsapp','news'].map(p => (
            <option key={p} value={p}>{p.charAt(0).toUpperCase() + p.slice(1)}</option>
          ))}
        </select>
        <select value={mkMoving} onChange={e => setMkMoving(e.target.value)} style={SELECT}>
          <option value="">Market-Moving: All</option>
          <option value="true">Market-Moving: Yes</option>
          <option value="false">Market-Moving: No</option>
        </select>
        <input
          placeholder="Filter by scrip…"
          value={scrip}
          onChange={e => setScrip(e.target.value.toUpperCase())}
          style={{ ...SELECT, width: 160 }}
        />
        <button
          onClick={() => setTick(t => t + 1)}
          style={{
            background: 'transparent',
            border: '1px solid var(--accent-green)',
            color: 'var(--accent-green)',
            fontFamily: 'var(--font-mono)', fontSize: 10,
            letterSpacing: 1.5, padding: '5px 14px',
            borderRadius: 2, cursor: 'pointer',
          }}
        >
          ↺ REFRESH
        </button>
        <span style={{ fontFamily: 'var(--font-mono)', fontSize: 9, color: 'var(--text-dim)', marginLeft: 'auto' }}>
          {signals.length} signals
        </span>
      </div>

      {/* ── Table ──────────────────────────────────────────────────────── */}
      <div style={{
        background: 'var(--bg-card)',
        border: '1px solid var(--border)',
        borderRadius: 4,
        overflow: 'auto',
      }}>
        {signals.length === 0 ? (
          <div style={{
            padding: 40, textAlign: 'center',
            fontFamily: 'var(--font-mono)', fontSize: 11, color: 'var(--text-dim)', letterSpacing: 1.5,
          }}>
            NO SIGNALS FOUND
          </div>
        ) : (
          <table style={{ width: '100%', borderCollapse: 'collapse', tableLayout: 'auto' }}>
            <thead>
              <tr>
                {['TIME','TYPE','PLATFORM','SCRIPS','THREAT SCORE','MISINFO','SOCIAL','MARKET MOVING','ALERT'].map(h => (
                  <th key={h} style={TH}>{h}</th>
                ))}
              </tr>
            </thead>
            <tbody>
              {signals.map(sig => <SignalRow key={sig.id} sig={sig} />)}
            </tbody>
          </table>
        )}
      </div>
    </div>
  )
}

const SELECT = {
  background: 'var(--bg-base)',
  border: '1px solid var(--border)',
  color: 'var(--text-primary)',
  fontFamily: 'var(--font-mono)',
  fontSize: 10,
  padding: '5px 10px',
  borderRadius: 2,
  outline: 'none',
  cursor: 'pointer',
}
