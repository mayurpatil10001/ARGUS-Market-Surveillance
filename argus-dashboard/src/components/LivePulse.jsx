export default function LivePulse({ active = true }) {
  return (
    <span style={{ display:'inline-flex', alignItems:'center', gap:5 }}>
      <span
        className={active ? 'live-pulse' : ''}
        style={{
          display:'inline-block', width:7, height:7,
          borderRadius:'50%',
          background: active ? 'var(--accent-green)' : 'var(--text-dim)',
          boxShadow: active ? '0 0 8px var(--accent-green)' : 'none',
        }}
      />
    </span>
  )
}
