import React from 'react'
import { api, downloadJson } from '../api.js'
import { Bar, Callout, Dropzone, Grid, Metric, ModeBadge, Pill, Ring, Section, Spinner, Subhead, sevKind, statusKind, useImageFile } from '../ui.jsx'

export default function Cracks({ onResult, result }) {
  const { file, setFile, preview } = useImageFile()
  const [busy, setBusy] = React.useState(false)
  const [error, setError] = React.useState('')
  const [overlay, setOverlay] = React.useState('')

  async function run() {
    setBusy(true); setError('')
    try {
      const res = await api.cracks(file)
      onResult(res.data); setOverlay(res.meta.overlay_image)
    } catch (e) { setError(e.message) } finally { setBusy(false) }
  }

  const r = result
  return (
    <div className="fade-in">
      <Section icon="🧱" title="Crack Diagnostics & Structural Integrity" subtitle="Classify defects, estimate width, score severity and get an engineering repair plan." />
      <div className="two-col">
        <div className="stack">
          <Dropzone file={file} onFile={setFile} preview={preview} label="Upload a concrete / wall surface photo" />
          <button className="btn primary" disabled={!file || busy} onClick={run} style={{ width: '100%' }}>🔬 Diagnose Defect</button>
        </div>
        <Callout kind="info">Tip: include a coin or ruler in the frame so crack width can be estimated more accurately. Classes: Hairline, Settlement, Structural Shear, Thermal Expansion, Spalling.</Callout>
      </div>
      {busy && <Spinner text="Running structural diagnosis..." />}
      {error && <Callout kind="error">⚠️ {error}</Callout>}

      {r && !busy && (
        <div className="fade-in">
          {r.notes.map((n) => <Callout key={n} kind="warn">{n}</Callout>)}
          <div className="report-head">
            <Ring score={r.severity_score} label="SEVERITY" invert />
            <div className="stack">
              <div className="row">
                <Pill kind={sevKind(r.severity_level)}>{r.severity_level.toUpperCase()} SEVERITY</Pill>
                <Pill kind={sevKind(r.severity_level)}>URGENCY: {r.urgency.toUpperCase()}</Pill>
                <ModeBadge mode={r.analysis_mode} />
              </div>
              <Grid cols={3}>
                <Metric label="Defect type" value={r.defect_type} sub={r.orientation} />
                <Metric label="Est. crack width" value={`${r.estimated_width_mm} mm`} sub="IS 456 limit 0.3 mm" accent={r.estimated_width_mm > 0.3 ? 'red' : 'green'} />
                <Metric label="Confidence" value={`${Math.round(r.confidence * 100)}%`} sub="model self-assessment" accent="cyan" />
              </Grid>
            </div>
          </div>
          <Callout><b>Structural risk:</b> {r.structural_risk}<div className="metric-sub" style={{ marginTop: '.5rem' }}>Width vs. 3 mm critical reference</div><Bar pct={Math.min(r.estimated_width_mm / 3 * 100, 100)} /></Callout>

          <div className="two-col evidence">
            {overlay && <figure style={{ margin: 0 }}><img src={overlay} alt="Edge detection overlay" /><figcaption className="metric-sub">Edge-detection overlay (assistive) - red marks linear dark features</figcaption></figure>}
            <div className="card"><div className="hazard-title">Engineering summary</div><div className="remedy">{r.summary}</div><div className="hazard-meta" style={{ marginTop: '.8rem' }}>Monitoring plan</div><div className="remedy">{r.monitoring_plan}</div></div>
          </div>

          <div className="two-col">
            <div><Subhead>Probable Root Causes</Subhead><div className="stack">{r.root_causes.map((c) => <div className="card" key={c}>• {c}</div>)}</div></div>
            <div><Subhead>Recommended Engineering Repairs</Subhead>
              <div className="stack">{r.recommended_repairs.map((s, i) => (
                <div className="card step" key={i}><div className="step-num">{i + 1}</div><div><div className="hazard-title">{s.method} <Pill kind={statusKind(s.priority)}>{s.priority}</Pill></div><div className="remedy">{s.description}</div></div></div>
              ))}</div>
            </div>
          </div>
          <p className="metric-sub">Standards referenced: {r.standards_referenced.join(' · ')}</p>
          <button className="btn" onClick={() => downloadJson(r, 'crack_diagnostic.json')}>⬇️ Download JSON report</button>
          <details style={{ marginTop: '1rem' }}><summary>View structured JSON contract</summary><pre className="json">{JSON.stringify(r, null, 2)}</pre></details>
        </div>
      )}
    </div>
  )
}
