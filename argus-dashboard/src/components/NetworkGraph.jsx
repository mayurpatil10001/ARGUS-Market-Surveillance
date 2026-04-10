import { useEffect, useRef, useState } from 'react'
import * as d3 from 'd3'

const score2color = d3.scaleSequential()
  .domain([0, 10])
  .interpolator(d3.interpolateRgb('#00ff88', '#ff3355'))

export default function NetworkGraph({ nodes = [], edges = [] }) {
  const svgRef    = useRef(null)
  const simRef    = useRef(null)
  const [tooltip, setTooltip] = useState(null)

  useEffect(() => {
    if (!nodes?.length) return
    const W = svgRef.current.parentElement.clientWidth || 700
    const H = 500

    d3.select(svgRef.current).selectAll('*').remove()

    const svg = d3.select(svgRef.current)
      .attr('width', W).attr('height', H)

    const g = svg.append('g')

    // Zoom + pan
    svg.call(d3.zoom()
      .scaleExtent([0.3, 3])
      .on('zoom', e => g.attr('transform', e.transform))
    )

    // Links
    const maxCoin = Math.max(...edges.map(e => e.coincidence_count ?? 1), 1)

    const link = g.selectAll('line')
      .data(edges)
      .enter().append('line')
      .attr('stroke', '#1a1a2e')
      .attr('stroke-width', d => 1 + ((d.coincidence_count ?? 1) / maxCoin) * 3)

    // Nodes
    const nodeData = nodes.map(n => ({ ...n }))
    const nodeG = g.selectAll('g.node')
      .data(nodeData)
      .enter().append('g').attr('class','node')
      .call(d3.drag()
        .on('start', (e,d) => { if (!e.active) simRef.current.alphaTarget(0.3).restart(); d.fx=d.x; d.fy=d.y })
        .on('drag',  (e,d) => { d.fx=e.x; d.fy=e.y })
        .on('end',   (e,d) => { if (!e.active) simRef.current.alphaTarget(0); d.fx=null; d.fy=null })
      )

    // Outer pulse ring for flagged nodes
    nodeG.filter(d => d.flagged).append('circle')
      .attr('r', 14)
      .attr('fill', 'none')
      .attr('stroke', '#ff3355')
      .attr('stroke-width', 1.5)
      .attr('opacity', 0.4)
      .append('animate').attr('attributeName','r').attr('from',10).attr('to',20)
        .attr('dur','2s').attr('repeatCount','indefinite')

    nodeG.append('circle')
      .attr('r', d => d.flagged ? 10 : 7)
      .attr('fill', d => score2color(d.score ?? 0))
      .attr('stroke', d => d.flagged ? '#ff3355' : '#1a1a2e')
      .attr('stroke-width', 1.5)
      .style('cursor', 'pointer')

    nodeG.on('mouseenter', (e, d) => {
      const [px, py] = d3.pointer(e, svgRef.current)
      setTooltip({ x:px, y:py, node:d })
    }).on('mouseleave', () => setTooltip(null))

    // Simulation
    simRef.current = d3.forceSimulation(nodeData)
      .force('link', d3.forceLink(edges.map(e => ({ ...e }))).id(d => d.id).distance(80))
      .force('charge', d3.forceManyBody().strength(-200))
      .force('center', d3.forceCenter(W/2, H/2))
      .on('tick', () => {
        link
          .attr('x1', d => d.source.x).attr('y1', d => d.source.y)
          .attr('x2', d => d.target.x).attr('y2', d => d.target.y)
        nodeG.attr('transform', d => `translate(${d.x},${d.y})`)
      })

    return () => simRef.current?.stop()
  }, [nodes, edges])

  if (!nodes?.length) {
    return (
      <div style={{
        height:500, display:'flex', flexDirection:'column',
        alignItems:'center', justifyContent:'center',
        background:'var(--bg-card)', border:'1px solid var(--border)',
        position:'relative',
      }}>
        <div style={{ position:'relative', width:120, height:120, marginBottom:24 }}>
          {[1,2,3].map(i => (
            <div key={i} className="radar-ring" style={{
              position:'absolute', top:'50%', left:'50%',
              transform:'translate(-50%,-50%)',
              width: i*40, height:i*40,
              borderRadius:'50%',
              border:'1px solid var(--accent-green)',
              animationDelay:`${(i-1)*0.8}s`,
            }} />
          ))}
          <div style={{
            position:'absolute', top:'50%', left:'50%',
            transform:'translate(-50%,-50%)',
            width:10, height:10, borderRadius:'50%',
            background:'var(--accent-green)',
          }} />
        </div>
        <div style={{
          fontFamily:'var(--font-mono)', color:'var(--text-secondary)',
          letterSpacing:2, fontSize:11,
        }}>
          NO NETWORK DATA — ENTER ACCOUNT ID
        </div>
      </div>
    )
  }

  return (
    <div style={{ position:'relative', background:'var(--bg-card)', border:'1px solid var(--border)' }}>
      <div className="chart-grid-bg" style={{ position:'absolute', inset:0, opacity:0.3 }} />
      <svg ref={svgRef} style={{ display:'block', position:'relative' }} />

      {/* Tooltip */}
      {tooltip && (
        <div style={{
          position:'absolute',
          left: tooltip.x + 12, top: tooltip.y - 10,
          background:'var(--bg-card)',
          border:'1px solid var(--border-bright)',
          padding:'8px 12px',
          fontFamily:'var(--font-mono)',
          fontSize:11,
          pointerEvents:'none',
          zIndex:10,
        }}>
          <div style={{color:'var(--text-primary)', fontWeight:600}}>{tooltip.node.id}</div>
          <div style={{color:'var(--text-secondary)', marginTop:2}}>
            Score: <span style={{color: score2color(tooltip.node.score??0)}}>{(tooltip.node.score??0).toFixed(2)}</span>
          </div>
          <div style={{color: tooltip.node.flagged ? 'var(--accent-red)' : 'var(--accent-green)', marginTop:2}}>
            {tooltip.node.flagged ? '⚑ FLAGGED' : '✓ NORMAL'}
          </div>
        </div>
      )}

      {/* Legend */}
      <div style={{
        position:'absolute', bottom:12, left:12,
        display:'flex', gap:8, alignItems:'center'
      }}>
        {[['LOW (0-4)', '#00ff88'], ['MED (4-7)','#ffb300'], ['HIGH (7-10)','#ff3355']].map(([l,c]) => (
          <div key={l} style={{ display:'flex', alignItems:'center', gap:4 }}>
            <div style={{ width:8, height:8, borderRadius:'50%', background:c }} />
            <span style={{ fontFamily:'var(--font-mono)', fontSize:9, color:'var(--text-secondary)' }}>{l}</span>
          </div>
        ))}
      </div>
    </div>
  )
}
