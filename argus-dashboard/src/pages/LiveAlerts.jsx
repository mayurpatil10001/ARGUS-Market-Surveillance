import { useState, useEffect, useRef } from 'react'
import { useQuery } from 'react-query'
import { motion } from 'framer-motion'
import toast from 'react-hot-toast'
import { api, connectLiveAlerts } from '../api/client'
import MetricCard from '../components/MetricCard'
import AlertRow from '../components/AlertRow'
import CaseModal from '../components/CaseModal'

const TABLE_HEADERS = ['SEVERITY','SCRIP','SCHEME TYPE','SCORE','ACCOUNTS','TIME','STATUS','']

function SkeletonRows({ n=5 }) {
  return (
    <>
      {Array.from({length:n}).map((_,i) => (
        <div key={i} style={{
          display:'grid', gridTemplateColumns:'90px 140px 140px 80px 100px 90px 110px 40px',
          padding:'10px 16px', gap:8, borderBottom:'1px solid var(--border)',
          alignItems:'center',
        }}>
          {[60,100,90,50,70,60,70,20].map((w,j) => (
            <div key={j} className="skeleton" style={{ height:12, width:`${w}%` }} />
          ))}
        </div>
      ))}
    </>
  )
}

export default function LiveAlerts() {
  const [filters, setFilters]   = useState({ scrip:'', status:'all', min_score:0 })
  const [page, setPage]         = useState(1)
  const [newIds, setNewIds]     = useState(new Set())
  const [caseAlert, setCaseAlert] = useState(null)
  const liveAlerts              = useRef([])

  const PER_PAGE = 10

  const { data, isLoading, isError, refetch } = useQuery(
    ['alerts', filters],
    () => api.getAlerts({
      scrip: filters.scrip || undefined,
      status: filters.status === 'all' ? undefined : filters.status,
      min_score: filters.min_score > 0 ? filters.min_score : undefined,
    }),
    { select: r => r.data }
  )

  useEffect(() => {
    const disconnect = connectLiveAlerts((alert) => {
      liveAlerts.current = [alert, ...liveAlerts.current]
      setNewIds(s => new Set([...s, alert.id]))
      toast.success(`NEW ALERT: ${alert.scrip} — ${Number(alert.impossibility_score).toFixed(1)}/10`, {
        duration: 5000,
      })
      refetch()
      setTimeout(() => setNewIds(s => { const n=new Set(s); n.delete(alert.id); return n }), 3000)
    })
    return disconnect
  }, [])

  const alerts = data?.alerts || []
  const total  = data?.total  || 0
  const open   = alerts.filter(a => a.status === 'open').length
  const avgScore = alerts.length
    ? (alerts.reduce((s,a) => s + a.impossibility_score, 0) / alerts.length).toFixed(1)
    : 0
  const totalAccs = alerts.reduce((s,a) => s + (a.accounts_involved?.length ?? 0), 0)
  const casesFiled = alerts.filter(a => a.status === 'case_filed').length

  const paged = alerts.slice((page-1)*PER_PAGE, page*PER_PAGE)
  const pages  = Math.ceil(alerts.length / PER_PAGE)

  return (
    <motion.div
      initial={{ opacity:0, y:-8 }}
      animate={{ opacity:1, y:0 }}
      transition={{ duration:0.2 }}
    >
      {/* Metric cards */}
      <div style={{ display:'grid', gridTemplateColumns:'repeat(4,1fr)', gap:16, marginBottom:24 }}>
        <MetricCard label="Active Alerts"    value={open}      color="var(--accent-red)"   delta={2} deltaLabel=" today" />
        <MetricCard label="Avg Score"        value={avgScore}  color="var(--accent-amber)"  unit="/10" />
        <MetricCard label="Accounts Watched" value={totalAccs} color="var(--accent-blue)" />
        <MetricCard label="Cases Filed"      value={casesFiled} color="var(--accent-green)" />
      </div>

      {/* Filter bar */}
      <div style={{
        display:'flex', gap:12, marginBottom:16, alignItems:'center',
        padding:'12px 16px',
        background:'var(--bg-card)', border:'1px solid var(--border)',
      }}>
        <input
          placeholder="SEARCH SCRIP..."
          value={filters.scrip}
          onChange={e => { setFilters(f=>({...f,scrip:e.target.value})); setPage(1) }}
          style={{ flex:1, maxWidth:220 }}
        />
        <select
          value={filters.status}
          onChange={e => { setFilters(f=>({...f,status:e.target.value})); setPage(1) }}
          style={{ width:160 }}
        >
          <option value="all">ALL STATUS</option>
          <option value="open">OPEN</option>
          <option value="under_review">UNDER REVIEW</option>
          <option value="case_filed">CASE FILED</option>
          <option value="resolved">RESOLVED</option>
          <option value="false_positive">FALSE POSITIVE</option>
        </select>
        <div style={{ display:'flex', alignItems:'center', gap:8 }}>
          <span style={{ fontFamily:'var(--font-mono)', fontSize:10, color:'var(--text-secondary)', whiteSpace:'nowrap' }}>
            MIN SCORE: {filters.min_score.toFixed(1)}
          </span>
          <input
            type="range" min={0} max={10} step={0.5}
            value={filters.min_score}
            onChange={e => { setFilters(f=>({...f,min_score:parseFloat(e.target.value)})); setPage(1) }}
            style={{ width:100, accentColor:'var(--accent-green)' }}
          />
        </div>
        <div style={{ fontFamily:'var(--font-mono)', fontSize:10, color:'var(--text-dim)', marginLeft:'auto' }}>
          {total} RECORDS
        </div>
      </div>

      {/* Table */}
      <div style={{ background:'var(--bg-card)', border:'1px solid var(--border)' }}>
        {/* Header */}
        <div style={{
          display:'grid',
          gridTemplateColumns:'90px 140px 140px 80px 100px 90px 110px 40px',
          padding:'8px 16px', gap:8,
          borderBottom:'1px solid var(--border-bright)',
          background:'var(--bg-surface)',
        }}>
          {TABLE_HEADERS.map(h => (
            <div key={h} style={{
              fontFamily:'var(--font-mono)', fontSize:9,
              color:'var(--text-dim)', letterSpacing:1.5,
            }}>{h}</div>
          ))}
        </div>

        {isLoading && <SkeletonRows />}

        {isError && (
          <div style={{ padding:40, textAlign:'center', color:'var(--accent-red)', fontFamily:'var(--font-mono)', fontSize:12 }}>
            SYSTEM OFFLINE — BACKEND UNAVAILABLE
            <br />
            <button onClick={refetch} style={{ marginTop:12, background:'transparent', border:'1px solid var(--accent-red)', color:'var(--accent-red)', padding:'6px 16px', fontFamily:'var(--font-mono)', fontSize:11, cursor:'pointer' }}>
              RETRY →
            </button>
          </div>
        )}

        {!isLoading && !isError && paged.length === 0 && (
          <div style={{ padding:60, textAlign:'center' }}>
            <div style={{ position:'relative', width:80, height:80, margin:'0 auto 20px' }}>
              {[1,2,3].map(i => (
                <div key={i} className="radar-ring" style={{
                  position:'absolute', top:'50%', left:'50%',
                  transform:'translate(-50%,-50%)',
                  width:i*26, height:i*26, borderRadius:'50%',
                  border:'1px solid var(--accent-green)',
                  animationDelay:`${(i-1)*0.8}s`,
                }} />
              ))}
            </div>
            <div style={{ fontFamily:'var(--font-mono)', color:'var(--text-secondary)', letterSpacing:2, fontSize:11 }}>
              NO ALERTS DETECTED — SYSTEM MONITORING
            </div>
          </div>
        )}

        {!isLoading && paged.map(alert => (
          <AlertRow
            key={alert.id}
            alert={alert}
            isNew={newIds.has(alert.id)}
            onGenerateCase={setCaseAlert}
          />
        ))}
      </div>

      {/* Pagination */}
      {pages > 1 && (
        <div style={{ display:'flex', gap:8, justifyContent:'center', marginTop:16 }}>
          {Array.from({length:pages}, (_,i) => i+1).map(n => (
            <button key={n} onClick={() => setPage(n)} style={{
              width:32, height:32,
              background: page===n ? 'var(--accent-green)' : 'var(--bg-card)',
              color: page===n ? '#000' : 'var(--text-secondary)',
              border:'1px solid var(--border)',
              fontFamily:'var(--font-mono)', fontSize:11,
              cursor:'pointer',
            }}>{n}</button>
          ))}
        </div>
      )}

      {/* Case modal */}
      {caseAlert && (
        <CaseModal
          alert={caseAlert}
          onClose={() => setCaseAlert(null)}
          onGenerated={() => setCaseAlert(null)}
        />
      )}
    </motion.div>
  )
}
