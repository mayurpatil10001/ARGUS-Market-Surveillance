/**
 * src/pages/MRFEAnalysis.jsx — Market Reaction Fingerprint Engine page.
 * Dark military theme. Tabs: Analyze Text | Upload File.
 * Displays: threat gauge, impact badge, event type, scrips, evidence, sparklines.
 */
import { useState, useRef } from 'react'
import { argusApi } from '../lib/api'
import ScoreGauge from '../components/ScoreGauge'
import SchemeBadge from '../components/SchemeBadge'
import {
  LineChart, Line, XAxis, YAxis, Tooltip, ResponsiveContainer
} from 'recharts'

// ── Helpers ─────────────────────────────────────────────────────────────────
const IMPACT_COLORS = {
  low:      { bg: 'rgba(34,197,94,0.15)',  border: '#22c55e', text: '#22c55e' },
  medium:   { bg: 'rgba(234,179,8,0.15)', border: '#eab308', text: '#eab308' },
  high:     { bg: 'rgba(249,115,22,0.15)',border: '#f97316', text: '#f97316' },
  critical: { bg: 'rgba(239,68,68,0.15)', border: '#ef4444', text: '#ef4444' },
}

function ImpactBadge({ level }) {
  const c = IMPACT_COLORS[level] || IMPACT_COLORS.low
  return (
    <span style={{
      display: 'inline-block',
      padding: '3px 10px',
      borderRadius: 4,
      background: c.bg,
      border: `1px solid ${c.border}`,
      color: c.text,
      fontFamily: 'var(--font-mono)',
      fontSize: 11,
      fontWeight: 700,
      letterSpacing: 2,
      textTransform: 'uppercase',
    }}>
      {level}
    </span>
  )
}

function ScripChip({ name }) {
  return (
    <span style={{
      display: 'inline-block',
      padding: '2px 8px',
      background: 'rgba(34,211,238,0.1)',
      border: '1px solid rgba(34,211,238,0.3)',
      borderRadius: 3,
      color: 'var(--accent-green)',
      fontFamily: 'var(--font-mono)',
      fontSize: 11,
      fontWeight: 600,
      letterSpacing: 1,
    }}>{name}</span>
  )
}

function ActionBox({ action }) {
  if (!action) return null
  const color = action.includes('freeze') || action.includes('escalate')
    ? '#ef4444' : action.includes('flag') ? '#f97316'
    : action.includes('monitor') ? '#eab308' : '#71717a'
  return (
    <div style={{
      marginTop: 16,
      padding: '12px 16px',
      background: `${color}14`,
      border: `1px solid ${color}55`,
      borderRadius: 6,
      display: 'flex', alignItems: 'center', gap: 10,
    }}>
      <span style={{ color, fontSize: 18 }}>⚡</span>
      <div>
        <div style={{ fontSize: 9, color: 'var(--text-dim)', fontFamily: 'var(--font-mono)', letterSpacing: 2 }}>
          RECOMMENDED ACTION
        </div>
        <div style={{ color, fontFamily: 'var(--font-mono)', fontSize: 12, fontWeight: 700, marginTop: 3, letterSpacing: 1 }}>
          {action.replace(/_/g, ' ').toUpperCase()}
        </div>
      </div>
    </div>
  )
}

function Sparkline({ scrip, data }) {
  if (!data || !data.prices) return null
  const chartData = data.prices.map((p, i) => ({ day: data.dates?.[i] || `D${i}`, price: p }))
  const first = chartData[0]?.price || 0
  const last = chartData[chartData.length - 1]?.price || 0
  const pct = first ? ((last - first) / first * 100).toFixed(2) : '0.00'
  const color = pct >= 0 ? '#22c55e' : '#ef4444'

  return (
    <div style={{ marginTop: 12, padding: '12px 14px', background: 'rgba(255,255,255,0.03)', borderRadius: 6, border: '1px solid var(--border)' }}>
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 8 }}>
        <span style={{ fontFamily: 'var(--font-mono)', fontWeight: 700, color: 'var(--accent-green)', fontSize: 12 }}>{scrip}</span>
        <span style={{ fontFamily: 'var(--font-mono)', fontSize: 11, color, fontWeight: 700 }}>
          {pct >= 0 ? '+' : ''}{pct}%{data.synthetic_data ? ' (synthetic)' : ''}
        </span>
      </div>
      <ResponsiveContainer width="100%" height={56}>
        <LineChart data={chartData} margin={{ top: 2, right: 2, bottom: 0, left: 0 }}>
          <Line type="monotone" dataKey="price" stroke={color} strokeWidth={1.5} dot={false} />
          <XAxis dataKey="day" hide />
          <YAxis domain={['auto', 'auto']} hide />
          <Tooltip
            contentStyle={{ background: 'var(--bg-card)', border: '1px solid var(--border)', borderRadius: 4, fontSize: 10, fontFamily: 'var(--font-mono)' }}
            labelStyle={{ color: 'var(--text-dim)' }}
            itemStyle={{ color }}
          />
        </LineChart>
      </ResponsiveContainer>
    </div>
  )
}

function AnalysisResult({ result }) {
  const [evidenceOpen, setEvidenceOpen] = useState(false)
  if (!result) return null

  return (
    <div style={{ marginTop: 24 }}>
      {/* Top row: gauge + badges */}
      <div style={{ display: 'flex', gap: 24, flexWrap: 'wrap', alignItems: 'flex-start' }}>
        <div style={{ textAlign: 'center' }}>
          <div style={{ fontSize: 9, color: 'var(--text-dim)', fontFamily: 'var(--font-mono)', letterSpacing: 2, marginBottom: 6 }}>
            THREAT SCORE
          </div>
          {/* ScoreGauge expects 0-10, MRFE returns 0-1 */}
          <ScoreGauge score={+(result.threat_score * 10).toFixed(1)} />
        </div>

        <div style={{ flex: 1, display: 'flex', flexDirection: 'column', gap: 10 }}>
          <div style={{ display: 'flex', gap: 10, flexWrap: 'wrap', alignItems: 'center' }}>
            <div>
              <div style={{ fontSize: 9, color: 'var(--text-dim)', fontFamily: 'var(--font-mono)', letterSpacing: 2, marginBottom: 4 }}>IMPACT</div>
              <ImpactBadge level={result.market_impact || 'low'} />
            </div>
            <div>
              <div style={{ fontSize: 9, color: 'var(--text-dim)', fontFamily: 'var(--font-mono)', letterSpacing: 2, marginBottom: 4 }}>EVENT TYPE</div>
              <SchemeBadge scheme={result.event_type || 'unknown'} />
            </div>
          </div>

          {/* Score row */}
          <div style={{ display: 'flex', gap: 16, flexWrap: 'wrap' }}>
            {[
              { label: 'MISINFO', val: result.misinfo_score },
              { label: 'SOCIAL', val: result.social_score },
              { label: 'THREAT', val: result.threat_adapter_score },
              { label: 'CONFIDENCE', val: result.confidence },
            ].map(({ label, val }) => (
              <div key={label}>
                <div style={{ fontSize: 8, color: 'var(--text-dim)', fontFamily: 'var(--font-mono)', letterSpacing: 1.5 }}>{label}</div>
                <div style={{ fontFamily: 'var(--font-mono)', fontSize: 14, fontWeight: 700, color: 'var(--text-primary)', marginTop: 2 }}>
                  {(+(val || 0) * 100).toFixed(0)}<span style={{ fontSize: 9, color: 'var(--text-dim)' }}>%</span>
                </div>
              </div>
            ))}
          </div>
        </div>
      </div>

      {/* Scrips */}
      {result.affected_scrips?.length > 0 && (
        <div style={{ marginTop: 16 }}>
          <div style={{ fontSize: 9, color: 'var(--text-dim)', fontFamily: 'var(--font-mono)', letterSpacing: 2, marginBottom: 6 }}>AFFECTED SCRIPS</div>
          <div style={{ display: 'flex', flexWrap: 'wrap', gap: 6 }}>
            {result.affected_scrips.map(s => <ScripChip key={s} name={s} />)}
          </div>
        </div>
      )}

      {/* Action */}
      <ActionBox action={result.recommended_action} />

      {/* Evidence */}
      {result.evidence_snippets?.length > 0 && (
        <div style={{ marginTop: 16 }}>
          <button
            onClick={() => setEvidenceOpen(o => !o)}
            style={{
              display: 'flex', alignItems: 'center', gap: 6,
              background: 'transparent', border: 'none', cursor: 'pointer',
              color: 'var(--text-secondary)', fontFamily: 'var(--font-mono)', fontSize: 11,
              padding: 0,
            }}
          >
            <span style={{ color: 'var(--accent-green)' }}>{evidenceOpen ? '▼' : '▶'}</span>
            EVIDENCE SNIPPETS ({result.evidence_snippets.length})
          </button>
          {evidenceOpen && (
            <div style={{ marginTop: 8, display: 'flex', flexDirection: 'column', gap: 6 }}>
              {result.evidence_snippets.map((s, i) => (
                <div key={i} style={{
                  padding: '8px 12px',
                  background: 'rgba(255,255,255,0.03)',
                  border: '1px solid var(--border)',
                  borderRadius: 4,
                  fontSize: 11,
                  color: 'var(--text-secondary)',
                  fontFamily: 'var(--font-mono)',
                  lineHeight: 1.5,
                }}>
                  <span style={{ color: 'var(--accent-green)' }}>[{i + 1}]</span> {s}
                </div>
              ))}
            </div>
          )}
        </div>
      )}

      {/* Historical sparklines */}
      {result.historical_context && Object.keys(result.historical_context).length > 0 && (
        <div style={{ marginTop: 20 }}>
          <div style={{ fontSize: 9, color: 'var(--text-dim)', fontFamily: 'var(--font-mono)', letterSpacing: 2, marginBottom: 4 }}>
            30-DAY PRICE CONTEXT
          </div>
          {Object.entries(result.historical_context).map(([scrip, data]) => (
            <Sparkline key={scrip} scrip={scrip} data={data} />
          ))}
        </div>
      )}

      {/* Processing time */}
      <div style={{ marginTop: 12, fontSize: 9, color: 'var(--text-dim)', fontFamily: 'var(--font-mono)' }}>
        ⏱ Processed in {result.processing_time_ms?.toFixed(1)} ms
        {result.pdf_pages != null && ` · ${result.pdf_pages} page(s), ${result.pdf_word_count?.toLocaleString()} words`}
        {result.synthetic_data && ' · synthetic_data:true'}
      </div>

      {result.note && (
        <div style={{ marginTop: 6, fontSize: 9, color: 'var(--text-dim)', fontFamily: 'var(--font-mono)', fontStyle: 'italic' }}>
          {result.note}
        </div>
      )}
    </div>
  )
}

// ── Main page ────────────────────────────────────────────────────────────────
export default function MRFEAnalysis() {
  const [activeTab, setActiveTab] = useState('text')
  const [text, setText] = useState('')
  const [fetchHistorical, setFetchHistorical] = useState(false)
  const [result, setResult] = useState(null)
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState(null)
  const [dragOver, setDragOver] = useState(false)
  const [selectedFile, setSelectedFile] = useState(null)
  const fileRef = useRef()

  async function analyzeText() {
    if (!text.trim()) return
    setLoading(true); setError(null); setResult(null)
    try {
      const token = localStorage.getItem('argus_token')
      const resp = await fetch('/mrfe/analyze/text', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json', Authorization: `Bearer ${token}` },
        body: JSON.stringify({ text, fetch_historical: fetchHistorical }),
      })
      if (!resp.ok) throw new Error(`${resp.status} ${resp.statusText}`)
      setResult(await resp.json())
    } catch (e) {
      setError(e.message)
    } finally {
      setLoading(false)
    }
  }

  async function analyzeFile() {
    if (!selectedFile) return
    setLoading(true); setError(null); setResult(null)
    try {
      const token = localStorage.getItem('argus_token')
      const fd = new FormData()
      fd.append('file', selectedFile)
      const resp = await fetch(`/mrfe/analyze/file?fetch_historical=${fetchHistorical}`, {
        method: 'POST',
        headers: { Authorization: `Bearer ${token}` },
        body: fd,
      })
      if (!resp.ok) throw new Error(`${resp.status} ${resp.statusText}`)
      setResult(await resp.json())
    } catch (e) {
      setError(e.message)
    } finally {
      setLoading(false)
    }
  }

  const tabStyle = (tab) => ({
    padding: '8px 20px',
    background: activeTab === tab ? 'rgba(34,211,238,0.08)' : 'transparent',
    border: 'none',
    borderBottom: activeTab === tab ? '2px solid var(--accent-green)' : '2px solid transparent',
    color: activeTab === tab ? 'var(--accent-green)' : 'var(--text-secondary)',
    fontFamily: 'var(--font-mono)',
    fontSize: 11,
    letterSpacing: 2,
    cursor: 'pointer',
    transition: 'all 0.15s',
  })

  return (
    <div style={{ maxWidth: 900, margin: '0 auto' }}>
      {/* Header */}
      <div style={{ marginBottom: 24 }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: 12 }}>
          <div style={{
            width: 36, height: 36, borderRadius: 6,
            background: 'rgba(34,211,238,0.1)',
            border: '1px solid rgba(34,211,238,0.3)',
            display: 'flex', alignItems: 'center', justifyContent: 'center',
            fontSize: 18,
          }}>🔍</div>
          <div>
            <h1 style={{ fontFamily: 'var(--font-display)', fontSize: 22, fontWeight: 800, color: 'var(--text-primary)', letterSpacing: 3, margin: 0 }}>
              MRFE ANALYSIS
            </h1>
            <div style={{ fontSize: 9, color: 'var(--text-dim)', fontFamily: 'var(--font-mono)', letterSpacing: 2, marginTop: 2 }}>
              MARKET REACTION FINGERPRINT ENGINE — TEXT / PDF / DOCUMENT
            </div>
          </div>
        </div>
      </div>

      {/* Card */}
      <div style={{ background: 'var(--bg-card)', border: '1px solid var(--border)', borderRadius: 8 }}>
        {/* Tabs */}
        <div style={{ display: 'flex', borderBottom: '1px solid var(--border)' }}>
          <button style={tabStyle('text')} onClick={() => { setActiveTab('text'); setResult(null); setError(null) }}>
            📝 ANALYZE TEXT
          </button>
          <button style={tabStyle('file')} onClick={() => { setActiveTab('file'); setResult(null); setError(null) }}>
            📎 UPLOAD FILE
          </button>
        </div>

        <div style={{ padding: 24 }}>
          {activeTab === 'text' && (
            <>
              <textarea
                value={text}
                onChange={e => setText(e.target.value)}
                placeholder="Paste financial news, social media posts, regulatory notices, or any text to analyze for market threats..."
                rows={8}
                style={{
                  width: '100%',
                  background: 'rgba(0,0,0,0.3)',
                  border: '1px solid var(--border)',
                  borderRadius: 6,
                  padding: '12px 14px',
                  color: 'var(--text-primary)',
                  fontFamily: 'var(--font-mono)',
                  fontSize: 12,
                  lineHeight: 1.6,
                  resize: 'vertical',
                  outline: 'none',
                  boxSizing: 'border-box',
                }}
              />
              <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginTop: 12 }}>
                <label style={{ display: 'flex', alignItems: 'center', gap: 8, cursor: 'pointer', fontFamily: 'var(--font-mono)', fontSize: 11, color: 'var(--text-secondary)' }}>
                  <input
                    type="checkbox"
                    checked={fetchHistorical}
                    onChange={e => setFetchHistorical(e.target.checked)}
                    style={{ accentColor: 'var(--accent-green)' }}
                  />
                  FETCH 30-DAY PRICE HISTORY FOR AFFECTED SCRIPS
                </label>
                <button
                  onClick={analyzeText}
                  disabled={loading || !text.trim()}
                  style={{
                    padding: '8px 22px',
                    background: loading ? 'rgba(34,211,238,0.1)' : 'rgba(34,211,238,0.15)',
                    border: '1px solid var(--accent-green)',
                    borderRadius: 6,
                    color: 'var(--accent-green)',
                    fontFamily: 'var(--font-mono)',
                    fontSize: 11,
                    fontWeight: 700,
                    letterSpacing: 2,
                    cursor: loading ? 'wait' : 'pointer',
                    opacity: loading || !text.trim() ? 0.55 : 1,
                    transition: 'all 0.15s',
                  }}
                >
                  {loading ? 'ANALYZING...' : 'ANALYZE'}
                </button>
              </div>
            </>
          )}

          {activeTab === 'file' && (
            <>
              <div
                onDragOver={e => { e.preventDefault(); setDragOver(true) }}
                onDragLeave={() => setDragOver(false)}
                onDrop={e => {
                  e.preventDefault(); setDragOver(false)
                  const f = e.dataTransfer.files[0]
                  if (f) setSelectedFile(f)
                }}
                onClick={() => fileRef.current?.click()}
                style={{
                  border: `2px dashed ${dragOver ? 'var(--accent-green)' : 'var(--border)'}`,
                  borderRadius: 8,
                  padding: '40px 24px',
                  textAlign: 'center',
                  cursor: 'pointer',
                  background: dragOver ? 'rgba(34,211,238,0.04)' : 'rgba(0,0,0,0.2)',
                  transition: 'all 0.15s',
                }}
              >
                <div style={{ fontSize: 32, marginBottom: 8 }}>📄</div>
                <div style={{ fontFamily: 'var(--font-mono)', fontSize: 12, color: 'var(--text-secondary)', marginBottom: 6 }}>
                  {selectedFile ? selectedFile.name : 'Drop file here or click to browse'}
                </div>
                <div style={{ fontFamily: 'var(--font-mono)', fontSize: 10, color: 'var(--text-dim)' }}>
                  Supported: PDF · TXT · CSV · DOCX · Max 10 MB
                </div>
              </div>
              <input
                ref={fileRef}
                type="file"
                accept=".pdf,.txt,.csv,.docx"
                style={{ display: 'none' }}
                onChange={e => e.target.files[0] && setSelectedFile(e.target.files[0])}
              />
              <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginTop: 12 }}>
                <label style={{ display: 'flex', alignItems: 'center', gap: 8, cursor: 'pointer', fontFamily: 'var(--font-mono)', fontSize: 11, color: 'var(--text-secondary)' }}>
                  <input
                    type="checkbox"
                    checked={fetchHistorical}
                    onChange={e => setFetchHistorical(e.target.checked)}
                    style={{ accentColor: 'var(--accent-green)' }}
                  />
                  FETCH 30-DAY PRICE HISTORY FOR AFFECTED SCRIPS
                </label>
                <button
                  onClick={analyzeFile}
                  disabled={loading || !selectedFile}
                  style={{
                    padding: '8px 22px',
                    background: 'rgba(34,211,238,0.15)',
                    border: '1px solid var(--accent-green)',
                    borderRadius: 6,
                    color: 'var(--accent-green)',
                    fontFamily: 'var(--font-mono)',
                    fontSize: 11,
                    fontWeight: 700,
                    letterSpacing: 2,
                    cursor: loading ? 'wait' : 'pointer',
                    opacity: loading || !selectedFile ? 0.55 : 1,
                    transition: 'all 0.15s',
                  }}
                >
                  {loading ? 'ANALYZING...' : 'ANALYZE FILE'}
                </button>
              </div>
            </>
          )}

          {/* Error */}
          {error && (
            <div style={{
              marginTop: 16, padding: '10px 14px',
              background: 'rgba(239,68,68,0.1)', border: '1px solid #ef444455',
              borderRadius: 6, color: '#ef4444', fontFamily: 'var(--font-mono)', fontSize: 11,
            }}>
              ⚠ {error}
            </div>
          )}

          {/* Results */}
          <AnalysisResult result={result} />
        </div>
      </div>
    </div>
  )
}
