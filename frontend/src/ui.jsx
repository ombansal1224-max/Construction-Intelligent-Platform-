import React from 'react'

const SEV = { Low: 'info', Medium: 'warn', High: 'bad', Critical: 'crit' }
const STATUS = {
  Compliant: 'ok', 'Needs Attention': 'warn', 'High Risk': 'bad', Critical: 'crit', Violation: 'crit',
  'Not Visible': 'muted', Go: 'ok', Restrict: 'warn', Suspend: 'crit', Completed: 'ok', 'In Progress': 'warn',
  Pending: 'muted', Primary: 'bad', Secondary: 'warn', Preventive: 'info',
}
export const sevKind = (s) => SEV[s] || 'muted'
export const statusKind = (s) => STATUS[s] || 'muted'

export const Pill = ({ kind = 'muted', live, children }) => (
  <span className={`pill pill-${kind}${live ? ' pill-live' : ''}`}>{children}</span>
)

export const Metric = ({ label, value, sub, accent = 'amber' }) => (
  <div className={`card accent-${accent}`}>
    <div className="metric-label">{label}</div>
    <div className="metric-value">{value}</div>
    {sub && <div className="metric-sub">{sub}</div>}
  </div>
)

export const Grid = ({ cols = 3, children }) => (
  <div className="grid" style={{ '--cols': cols }}>{children}</div>
)

export const Section = ({ icon, title, subtitle }) => (
  <div style={{ marginBottom: '1rem' }}>
    <h2 className="section-title">{icon} {title}</h2>
    <p className="section-sub">{subtitle}</p>
  </div>
)

export const Subhead = ({ children }) => <h3 className="subhead">{children}</h3>

export const Callout = ({ kind = 'info', children }) => <div className={`callout callout-${kind}`}>{children}</div>

export const Bar = ({ pct }) => (
  <div className="bar"><span style={{ width: `${Math.max(0, Math.min(100, pct))}%` }} /></div>
)

export function Ring({ score, label, invert = false }) {
  const good = invert ? 100 - score : score
  const color = good >= 75 ? '#34d399' : good >= 50 ? '#ffb020' : good >= 30 ? '#ff7a1a' : '#fb5470'
  return (
    <div className="ring" style={{ '--p': score, '--c': color }}>
      <div className="ring-num">{Math.round(score)}<small>{label}</small></div>
    </div>
  )
}

export const ModeBadge = ({ mode }) =>
  mode === 'gemini' ? <Pill kind="ok" live>LIVE · GEMINI</Pill> : <Pill kind="warn">DEMO MODE</Pill>

export function Dropzone({ file, onFile, preview, label }) {
  const inputRef = React.useRef(null)
  const [over, setOver] = React.useState(false)
  const pick = (f) => f && /^image\/(jpeg|png)$/.test(f.type) && onFile(f)
  return (
    <div
      className={`dropzone${over ? ' over' : ''}`}
      onClick={() => inputRef.current?.click()}
      onDragOver={(e) => { e.preventDefault(); setOver(true) }}
      onDragLeave={() => setOver(false)}
      onDrop={(e) => { e.preventDefault(); setOver(false); pick(e.dataTransfer.files[0]) }}
      role="button" tabIndex={0} aria-label={label}
    >
      <input ref={inputRef} type="file" accept="image/jpeg,image/png" hidden onChange={(e) => pick(e.target.files[0])} />
      {preview ? <img src={preview} alt="Selected upload preview" /> : (
        <div className="drop-hint"><div style={{ fontSize: '2.2rem' }}>📤</div><b>{label}</b><div className="metric-sub">Drag & drop or click · JPG / PNG · max 10 MB</div></div>
      )}
      {file && <div className="metric-sub" style={{ marginTop: '.5rem' }}>{file.name}</div>}
    </div>
  )
}

export function useImageFile() {
  const [file, setFile] = React.useState(null)
  const [preview, setPreview] = React.useState('')
  React.useEffect(() => {
    if (!file) { setPreview(''); return }
    const url = URL.createObjectURL(file)
    setPreview(url)
    return () => URL.revokeObjectURL(url)
  }, [file])
  return { file, setFile, preview }
}

export const Spinner = ({ text }) => <div className="spinner-row"><span className="spinner" /> {text}</div>
