import React from 'react'
import { api, formatInr, num } from '../api.js'
import { Bar, Callout, Grid, Metric, Pill, Section, Spinner, Subhead, statusKind } from '../ui.jsx'

export default function Planning({ config, onResult }) {
  const [form, setForm] = React.useState({ structure: 'Independent House / Villa', sqft: 2400, tier: 'Tier 2', completion_pct: 45, grade: 'Standard' })
  const [res, setRes] = React.useState(null)
  const [error, setError] = React.useState('')
  const [render, setRender] = React.useState({ style: 'Contemporary Indian', time_of_day: 'Golden hour', city: '', prompt: '', url: '', busy: false })
  const set = (k) => (e) => setForm((f) => ({ ...f, [k]: e.target.type === 'number' || e.target.type === 'range' ? Number(e.target.value) : e.target.value }))

  // debounced live recomputation
  React.useEffect(() => {
    const t = setTimeout(async () => {
      try {
        const r = await api.valuation(form)
        setRes(r.data); setError(''); onResult(r.data)
      } catch (e) { setError(e.message) }
    }, 250)
    return () => clearTimeout(t)
  }, [form])

  async function generate() {
    setRender((r) => ({ ...r, busy: true }))
    try {
      const p = await api.renderPrompt({ structure: form.structure, tier: form.tier, completion_pct: form.completion_pct, style: render.style, city: render.city, time_of_day: render.time_of_day })
      const prompt = render.prompt || p.data.prompt
      const url = render.prompt ? p.data.image_url.replace(/prompt\/[^?]+/, `prompt/${encodeURIComponent(render.prompt)}`) : p.data.image_url
      setRender((r) => ({ ...r, prompt, url: `${url}&t=${Date.now() % 100000}`, busy: false }))
    } catch (e) { setError(e.message); setRender((r) => ({ ...r, busy: false })) }
  }

  const b = res?.budget, v = res?.valuation, m = res?.materials, s = res?.schedule
  return (
    <div className="fade-in">
      <Section icon="📐" title="Planning & Real Estate Valuation" subtitle="Interactive cost model for Indian construction: budget, capex, market valuation, materials and schedule." />
      <div className="card" style={{ marginBottom: '1rem' }}>
        <div className="form-grid">
          <div><label className="field" htmlFor="structure">Structure type</label>
            <select id="structure" value={form.structure} onChange={set('structure')}>{config?.structures.map((x) => <option key={x}>{x}</option>)}</select></div>
          <div><label className="field" htmlFor="sqft">Built-up area (sq ft)</label>
            <input id="sqft" type="number" min="100" max="5000000" step="100" value={form.sqft} onChange={set('sqft')} /></div>
          <div><label className="field" htmlFor="tier">Location tier</label>
            <select id="tier" value={form.tier} onChange={set('tier')}>{config && Object.keys(config.tiers).map((x) => <option key={x}>{x}</option>)}</select></div>
          <div><label className="field" htmlFor="grade">Finish grade</label>
            <select id="grade" value={form.grade} onChange={set('grade')}>{config?.grades.map((x) => <option key={x}>{x}</option>)}</select></div>
        </div>
        <label className="field" htmlFor="completion" style={{ marginTop: '1rem' }}>Completion percentage: <b style={{ color: 'var(--amber)' }}>{form.completion_pct}%</b></label>
        <input id="completion" type="range" min="0" max="100" value={form.completion_pct} onChange={set('completion_pct')} />
        <div className="metric-sub" style={{ marginTop: '.5rem' }}>📍 {config?.tiers[form.tier]?.examples}</div>
      </div>
      {error && <Callout kind="error">⚠️ {error}</Callout>}
      {!res && !error && <Spinner text="Calculating..." />}

      {res && (<>
        <Subhead>Financial Overview</Subhead>
        <Grid cols={4}>
          <Metric label="Total project budget" value={formatInr(b.total)} sub={`₹${num(b.per_sqft)}/sq ft · incl. ${b.contingency_pct}% contingency`} />
          <Metric label="Capex incurred" value={formatInr(b.capex_incurred)} sub={`${form.completion_pct}% · ${formatInr(b.remaining)} remaining`} accent="cyan" />
          <Metric label="Current market valuation" value={formatInr(v.current_value)} sub={`land ${formatInr(v.land_value)} + built value`} accent="green" />
          <Metric label="Value on completion" value={formatInr(v.value_on_completion)} sub={`ROI ${Math.round(v.roi_pct)}% · ₹${num(v.market_rate_per_sqft)}/sq ft`} accent="violet" />
        </Grid>
        <Subhead>Material Requirements</Subhead>
        <Grid cols={4}>
          <Metric label="Steel required" value={`${num(m.steel_total_tonnes, 1)} t`} sub={`${num(m.steel_consumed_kg / 1000, 1)} t used · ${num(m.steel_remaining_kg / 1000, 1)} t to procure`} />
          <Metric label="Cement required" value={`${num(m.cement_total_bags)} bags`} sub={`${num(m.cement_consumed_bags)} used · ${num(m.cement_remaining_bags)} to procure`} accent="cyan" />
          <Metric label="Steel procurement" value={formatInr(m.steel_cost)} sub="at ₹65 / kg (indicative)" accent="green" />
          <Metric label="Cement procurement" value={formatInr(m.cement_cost)} sub="at ₹390 / bag (indicative)" accent="violet" />
        </Grid>

        <Subhead>Milestone Progress</Subhead>
        <div className="card" style={{ marginBottom: '1rem' }}>
          <div className="spread"><b>Overall · {res.current_phase}</b><span className="metric-sub">{s.elapsed_months} of {s.total_months} months elapsed · {s.remaining_months} remaining</span></div>
          <Bar pct={form.completion_pct} />
        </div>
        <Grid cols={2}>
          {res.milestones.map((ms) => (
            <div className="card" key={ms.name}>
              <div className="spread"><span>{ms.name}</span><Pill kind={statusKind(ms.status)}>{ms.status}</Pill></div>
              <Bar pct={ms.progress_pct} />
              <div className="metric-sub" style={{ marginTop: '.4rem' }}>Budget {formatInr(ms.budget)} · Month {ms.start_month} → {(ms.start_month + ms.duration_months).toFixed(1)}</div>
            </div>
          ))}
        </Grid>

        <Subhead>Budget Allocation vs. Spend</Subhead>
        <div className="card bars">
          {b.breakdown.map((x) => (
            <div key={x.category}>
              <div className="lab"><span>{x.category}</span><span className="metric-sub">{formatInr(x.spent)} of {formatInr(x.amount)}</span></div>
              <div className="dual"><span style={{ width: `${form.completion_pct}%` }} /></div>
            </div>
          ))}
        </div>
      </>)}

      <Subhead>Conceptual 3D Architectural Rendering (Pollinations AI · Flux)</Subhead>
      <div className="card stack">
        <div className="form-grid" style={{ gridTemplateColumns: '1fr 1fr 1fr' }}>
          <div><label className="field" htmlFor="style">Architectural style</label>
            <select id="style" value={render.style} onChange={(e) => setRender({ ...render, style: e.target.value, prompt: '' })}>{config?.styles.map((x) => <option key={x}>{x}</option>)}</select></div>
          <div><label className="field" htmlFor="tod">Lighting</label>
            <select id="tod" value={render.time_of_day} onChange={(e) => setRender({ ...render, time_of_day: e.target.value, prompt: '' })}>{config?.times_of_day.map((x) => <option key={x}>{x}</option>)}</select></div>
          <div><label className="field" htmlFor="city">City (optional)</label>
            <input id="city" value={render.city} placeholder="e.g. Pune" onChange={(e) => setRender({ ...render, city: e.target.value, prompt: '' })} /></div>
        </div>
        {render.prompt && <textarea rows={3} value={render.prompt} onChange={(e) => setRender({ ...render, prompt: e.target.value })} aria-label="Editable image prompt" />}
        <div className="row"><button className="btn primary" onClick={generate} disabled={render.busy}>🎨 Generate concept render</button>
          {render.url && <a className="btn" href={render.url} target="_blank" rel="noreferrer" style={{ textDecoration: 'none' }}>↗ Open full size</a>}</div>
        {render.busy && <Spinner text="Building prompt..." />}
        {render.url && <div className="render-frame"><img src={render.url} alt="AI-generated concept render of the building" /></div>}
        <div className="metric-sub">First load can take 10-30 seconds. Images are generated on demand by Pollinations AI.</div>
      </div>
      <Callout kind="warn">Estimates are indicative planning figures from tier-adjusted benchmarks, not a certified valuation.</Callout>
    </div>
  )
}
