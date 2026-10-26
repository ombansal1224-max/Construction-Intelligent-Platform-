import React from 'react'
import { api, downloadJson } from '../api.js'
import { Bar, Callout, Dropzone, Grid, Metric, ModeBadge, Pill, Ring, Section, Spinner, Subhead, sevKind, statusKind, useImageFile } from '../ui.jsx'

const ICONS = { helmet: '⛑️', hi_vis_vest: '🦺', safety_boots: '🥾', safety_harness: '🪢' }

export default function Safety({ onResult, result }) {
  const { file, setFile, preview } = useImageFile()
  const [busy, setBusy] = React.useState(false)
  const [error, setError] = React.useState('')
  const [meta, setMeta] = React.useState(null)

  async function run() {
    setBusy(true); setError('')
    try {
      const res = await api.safety(file)
      onResult(res.data); setMeta(res.meta)
    } catch (e) { setError(e.message) } finally { setBusy(false) }
  }

  const r = result
  const violations = r?.ppe_detection.filter((p) => p.status === 'Violation').length ?? 0
  const severe = r?.hazards.filter((h) => ['High', 'Critical'].includes(h.severity)).length ?? 0

  return (
    <div className="fade-in">
      <Section icon="🦺" title="Site Safety & PPE Audit" subtitle="Multimodal audit of worker PPE and site hazards under OSHA 1926 and Indian IS standards." />
      <div className="two-col">
        <div className="stack">
          <Dropzone file={file} onFile={setFile} preview={preview} label="Upload a construction-site photo" />
          <button className="btn primary" disabled={!file || busy} onClick={run} style={{ width: '100%' }}>🔍 Run Safety Audit</button>
        </div>
        <Callout kind="info">The model checks <b>helmets, hi-vis vests, steel-toe boots and safety harnesses</b>, then lists hazards with severity and corrective remedies. A deterministic offline engine is used if no Gemini key is configured.</Callout>
      </div>
      {busy && <Spinner text="Analysing site photograph..." />}
      {error && <Callout kind="error">⚠️ {error}</Callout>}

      {r && !busy && (
        <div className="fade-in">
          {r.notes.map((n) => <Callout key={n} kind="warn">{n}</Callout>)}
          <div className="report-head">
            <Ring score={r.safety_score} label="SAFETY SCORE" />
            <div className="stack">
              <div className="row"><Pill kind={statusKind(r.overall_status)}>{r.overall_status.toUpperCase()}</Pill><ModeBadge mode={r.analysis_mode} /></div>
              <Grid cols={3}>
                <Metric label="Workers detected" value={r.workers_detected} sub="in frame" accent="cyan" />
                <Metric label="PPE violations" value={violations} sub={`of ${r.ppe_detection.length} categories`} accent={violations ? 'red' : 'green'} />
                <Metric label="Hazards" value={r.hazards.length} sub={`${severe} high / critical`} accent={severe ? 'red' : 'amber'} />
              </Grid>
            </div>
          </div>
          <Callout>{r.summary}</Callout>

          <Subhead>PPE Compliance Checklist</Subhead>
          <Grid cols={4}>
            {r.ppe_detection.map((p) => (
              <div className="card" key={p.item}>
                <div style={{ fontSize: '1.7rem' }}>{ICONS[p.item] || '🛡️'}</div>
                <div className="hazard-title" style={{ marginTop: '.25rem' }}>{p.label}</div>
                <Pill kind={statusKind(p.status)}>{p.status}</Pill>
                <Bar pct={p.confidence * 100} />
                <div className="metric-sub" style={{ marginTop: '.4rem' }}>Confidence {Math.round(p.confidence * 100)}%. {p.note}</div>
              </div>
            ))}
          </Grid>

          <Subhead>Identified Site Hazards</Subhead>
          <div className="stack">
            {r.hazards.length === 0 && <Callout>No hazards identified in this image.</Callout>}
            {r.hazards.map((h, i) => (
              <div className={`card hazard sev-${h.severity}`} key={i}>
                <div className="spread"><div className="hazard-title">{h.hazard}</div><Pill kind={sevKind(h.severity)}>{h.severity}</Pill></div>
                <div className="hazard-meta">{[h.location, h.standard_reference].filter(Boolean).join(' · ')}</div>
                <div className="remedy"><b>Remedy:</b> {h.remedy}</div>
              </div>
            ))}
          </div>

          {r.recommendations.length > 0 && (<><Subhead>Prioritised Recommendations</Subhead><ul>{r.recommendations.map((x) => <li key={x}>{x}</li>)}</ul></>)}
          <p className="metric-sub">Standards referenced: {r.standards_referenced.join(' · ')}{meta?.report_id && ` · Report ID ${meta.report_id.slice(0, 8)}`}</p>
          <button className="btn" onClick={() => downloadJson(r, 'safety_audit.json')}>⬇️ Download JSON report</button>
          <details style={{ marginTop: '1rem' }}><summary>View structured JSON contract</summary><pre className="json">{JSON.stringify(r, null, 2)}</pre></details>
        </div>
      )}
    </div>
  )
}
