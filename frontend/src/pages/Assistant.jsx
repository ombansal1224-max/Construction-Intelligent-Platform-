import React from 'react'
import { api } from '../api.js'
import { Callout, Grid, Metric, Pill, Section, Spinner, Subhead, sevKind, statusKind } from '../ui.jsx'

const ICONS = { Normal: '☀️', 'High Wind': '💨', 'Heavy Rain': '🌧️', 'Extreme Heat': '🔥' }
const SUGGESTIONS = ['How long should concrete be cured?', 'What are the PPE requirements on site?', 'When is a crack structurally dangerous?', 'Rules of thumb for steel and cement quantities?', 'How do I protect fresh concrete during rain?', 'What does RERA require for escrow funds?']

export default function Assistant({ config, context, condition, setCondition }) {
  const [adv, setAdv] = React.useState(null)
  const [err, setErr] = React.useState('')
  const [city, setCity] = React.useState('')
  const [live, setLive] = React.useState(null)
  const [messages, setMessages] = React.useState([])
  const [input, setInput] = React.useState('')
  const [busy, setBusy] = React.useState(false)
  const endRef = React.useRef(null)

  React.useEffect(() => {
    setAdv(null)
    api.advisory(condition).then((r) => { setAdv(r.data); setErr('') }).catch((e) => setErr(e.message))
  }, [condition])
  React.useEffect(() => { endRef.current?.scrollIntoView({ behavior: 'smooth' }) }, [messages, busy])

  async function fetchLive() {
    try { setLive((await api.liveWeather(city)).data); setErr('') } catch (e) { setLive(null); setErr(e.message) }
  }

  async function send(text) {
    const q = (text ?? input).trim()
    if (!q || busy) return
    const next = [...messages, { role: 'user', content: q }]
    setMessages(next); setInput(''); setBusy(true)
    try {
      const r = await api.chat(next, { ...context, weather_condition: condition })
      setMessages([...next, { role: 'assistant', content: r.data.answer }])
    } catch (e) {
      setMessages([...next, { role: 'assistant', content: `⚠️ ${e.message}` }])
    } finally { setBusy(false) }
  }

  return (
    <div className="fade-in">
      <Section icon="🌦️" title="Daily Site Assistant & Weather Advisory" subtitle="Weather-driven operating protocols plus an interactive construction engineering assistant." />
      <div className="chips" role="radiogroup" aria-label="Weather condition">
        {(config?.weather_conditions || Object.keys(ICONS)).map((c) => (
          <button key={c} className={`chip${c === condition ? ' active' : ''}`} onClick={() => setCondition(c)} role="radio" aria-checked={c === condition}>{ICONS[c]} {c}</button>
        ))}
      </div>

      <details style={{ margin: '1rem 0' }}>
        <summary>📡 Auto-detect from live weather (Open-Meteo, no key needed)</summary>
        <div className="row" style={{ marginTop: '.7rem' }}>
          <input style={{ maxWidth: 260 }} value={city} placeholder="City, e.g. Mumbai" onChange={(e) => setCity(e.target.value)} aria-label="City" />
          <button className="btn" onClick={fetchLive}>Fetch live weather</button>
        </div>
        {live && (<div style={{ marginTop: '.8rem' }}><Grid cols={4}>
          <Metric label="Location" value={live.location.split(',')[0]} sub={live.location} accent="cyan" />
          <Metric label="Feels like" value={`${Math.round(live.apparent_temperature_c)} °C`} sub={`air ${Math.round(live.temperature_c)} °C`} />
          <Metric label="Wind / gusts" value={`${Math.round(live.wind_kmh)} km/h`} sub={`gusts ${Math.round(live.gusts_kmh)} km/h`} accent="violet" />
          <Metric label="Rain now" value={`${live.precipitation_mm} mm`} sub="current hour" accent="cyan" />
        </Grid><Callout kind="info">Suggested advisory: <b>{live.suggested_condition}</b> <button className="chip" onClick={() => setCondition(live.suggested_condition)}>Apply</button></Callout></div>)}
      </details>
      {err && <Callout kind="error">⚠️ {err}</Callout>}
      {!adv && !err && <Spinner text="Loading advisory..." />}

      {adv && (<div className="fade-in">
        <div className="card spread" style={{ alignItems: 'center', marginBottom: '1rem' }}>
          <div><h3 className="section-title" style={{ margin: 0 }}>{adv.icon} {adv.headline}</h3><div className="metric-sub">Trigger: {adv.trigger}</div></div>
          <Pill kind={adv.risk === 'Low' ? 'ok' : 'crit'}>{adv.risk.toUpperCase()} RISK</Pill>
        </div>
        <Subhead>Dynamic Safety Alerts</Subhead>
        <Grid cols={2}>{adv.alerts.map((a) => (
          <div className={`card hazard sev-${a.severity}`} key={a.title}><div className="spread"><div className="hazard-title">{a.title}</div><Pill kind={sevKind(a.severity)}>{a.severity}</Pill></div><div className="remedy">{a.detail}</div></div>
        ))}</Grid>
        <Subhead>Operations Status Board</Subhead>
        <Grid cols={3}>{Object.entries(adv.operations).map(([op, [status, note]]) => (
          <div className="card" key={op}><div className="spread"><b>{op}</b><Pill kind={statusKind(status)}>{status.toUpperCase()}</Pill></div><div className="metric-sub" style={{ marginTop: '.3rem' }}>{note}</div></div>
        ))}</Grid>
        <div className="two-col">
          <div><Subhead>Concrete Curing Protocol</Subhead><div className="stack">{adv.curing.map((c) => <div className="card" key={c}>💧 {c}</div>)}</div></div>
          <div><Subhead>Required PPE Today</Subhead><div className="chips">{adv.ppe.map((p) => <Pill key={p} kind="info">{p}</Pill>)}</div>
            <Subhead>Pre-shift Checklist</Subhead>
            {adv.checklist.map((c) => <label key={c} style={{ display: 'flex', gap: '.5rem', margin: '.35rem 0' }}><input type="checkbox" style={{ width: 'auto' }} /> {c}</label>)}
            <div className="metric-sub">Standards: {adv.standards.join(' · ')}</div></div>
        </div>
      </div>)}

      <Subhead>💬 Construction Engineering Assistant</Subhead>
      <div className="card">
        {messages.length === 0 && <div className="chips" style={{ marginBottom: '.8rem' }}>{SUGGESTIONS.map((s) => <button key={s} className="chip" onClick={() => send(s)}>{s}</button>)}</div>}
        <div className="chat" aria-live="polite">
          {messages.map((m, i) => <div key={i} className={`bubble ${m.role}`}>{m.content}</div>)}
          {busy && <div className="bubble assistant"><Spinner text="Thinking..." /></div>}
          <div ref={endRef} />
        </div>
        <form className="chat-input" onSubmit={(e) => { e.preventDefault(); send() }}>
          <input value={input} onChange={(e) => setInput(e.target.value)} placeholder="Ask about concrete, safety, costs, codes, scheduling..." aria-label="Chat message" />
          <button className="btn primary" disabled={busy || !input.trim()}>Send</button>
          {messages.length > 0 && <button type="button" className="btn" onClick={() => setMessages([])}>Clear</button>}
        </form>
      </div>
    </div>
  )
}
