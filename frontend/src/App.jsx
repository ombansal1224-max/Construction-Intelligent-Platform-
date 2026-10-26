import React from 'react'
import { api, getKey, setKey } from './api.js'
import { ModeBadge, Pill } from './ui.jsx'
import Safety from './pages/Safety.jsx'
import Cracks from './pages/Cracks.jsx'
import Planning from './pages/Planning.jsx'
import Assistant from './pages/Assistant.jsx'

const NAV = [
  ['safety', '🦺', 'Site Safety & PPE'],
  ['cracks', '🧱', 'Crack Diagnostics'],
  ['planning', '📐', 'Planning & Valuation'],
  ['assistant', '🌦️', 'Site Assistant'],
]

export default function App() {
  const [page, setPage] = React.useState('safety')
  const [config, setConfig] = React.useState(null)
  const [apiOnline, setApiOnline] = React.useState(null)
  const [keyInput, setKeyInput] = React.useState(getKey())
  const [keyMsg, setKeyMsg] = React.useState('')
  const [shared, setShared] = React.useState({ safety: null, crack: null, valuation: null })
  const [condition, setCondition] = React.useState('Normal')

  React.useEffect(() => {
    api.health().then(() => setApiOnline(true)).catch(() => setApiOnline(false))
    api.config().then((r) => setConfig(r.data)).catch(() => {})
  }, [])

  const mode = keyInput.trim() ? 'gemini' : 'demo'
  const save = (k) => (v) => setShared((s) => ({ ...s, [k]: v }))

  async function saveKey() {
    setKey(keyInput.trim())
    if (!keyInput.trim()) return setKeyMsg('Key cleared - demo mode.')
    try {
      const r = await api.validateKey()
      setKeyMsg(r.data.valid ? '✅ Key verified.' : `❌ ${r.data.message}`)
    } catch (e) { setKeyMsg(e.message) }
  }

  // compact context for the chatbot
  const context = {
    valuation: shared.valuation || undefined,
    safety: shared.safety && { safety_score: shared.safety.safety_score, overall_status: shared.safety.overall_status, summary: shared.safety.summary, hazards: shared.safety.hazards.map((h) => h.hazard) },
    crack: shared.crack && { defect_type: shared.crack.defect_type, estimated_width_mm: shared.crack.estimated_width_mm, severity_level: shared.crack.severity_level, severity_score: shared.crack.severity_score, urgency: shared.crack.urgency },
  }

  return (
    <div className="shell">
      <aside className="sidebar">
        <div className="brand"><div className="brand-logo">🏗️</div><div><div className="brand-name">Construction Intelligence</div><div className="brand-sub">Multimodal AI Platform · v1.0</div></div></div>
        <nav className="nav" aria-label="Feature navigation">
          {NAV.map(([id, icon, label]) => <button key={id} className={page === id ? 'active' : ''} onClick={() => setPage(id)}>{icon} {label}</button>)}
        </nav>
        <div className="side-label">🔐 Gemini API key</div>
        <input type="password" value={keyInput} placeholder="Paste key for live AI" onChange={(e) => setKeyInput(e.target.value)} aria-label="Gemini API key" autoComplete="off" />
        <div className="row" style={{ marginTop: '.6rem' }}><button className="btn" onClick={saveKey} style={{ padding: '.45rem .9rem' }}>Save & verify</button><ModeBadge mode={mode} /></div>
        {keyMsg && <div className="metric-sub" style={{ marginTop: '.5rem' }}>{keyMsg}</div>}
        <div className="metric-sub" style={{ marginTop: '.5rem' }}>Held in this tab only (sessionStorage). Leave empty for demo mode.</div>
        <div className="side-label">System</div>
        <div className="row"><Pill kind={apiOnline ? 'ok' : apiOnline === false ? 'crit' : 'muted'}>API {apiOnline ? 'ONLINE' : apiOnline === false ? 'OFFLINE' : '...'}</Pill></div>
        <div className="side-label">Architecture</div>
        <div className="metric-sub" style={{ lineHeight: 1.7 }}>React → User Input → FastAPI ⇄ File Storage → Multimodal AI → Safety · Cracks · Valuation · Planning · Weather</div>
        <p className="metric-sub" style={{ marginTop: '1.2rem' }}>⚠️ Decision-support only. Verify with a licensed engineer.</p>
      </aside>
      <main className="main">
        <header className="hero"><div className="hero-kicker">AI · Construction · Real Estate Decision Support</div><h1>Multimodal Construction Intelligence Platform</h1>
          <p>Audit PPE compliance, diagnose concrete cracks, value your project in ₹ and get weather-aware daily protocols - strict JSON contracts end to end.</p></header>
        {apiOnline === false && <div className="callout callout-error">⚠️ Backend unreachable. Run <code>uvicorn backend.main:app --port 8000</code> from the project root.</div>}
        {page === 'safety' && <Safety result={shared.safety} onResult={save('safety')} />}
        {page === 'cracks' && <Cracks result={shared.crack} onResult={save('crack')} />}
        {page === 'planning' && <Planning config={config} onResult={save('valuation')} />}
        {page === 'assistant' && <Assistant config={config} context={context} condition={condition} setCondition={setCondition} />}
      </main>
    </div>
  )
}
