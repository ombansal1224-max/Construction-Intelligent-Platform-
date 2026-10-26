// Thin client for the FastAPI backend. Every response follows {status, data, meta} | {status:'error', error}.
const KEY = 'gemini_api_key'

export const getKey = () => sessionStorage.getItem(KEY) || ''
export const setKey = (k) => (k ? sessionStorage.setItem(KEY, k) : sessionStorage.removeItem(KEY))

async function request(path, { method = 'GET', json, form } = {}) {
  const headers = {}
  const key = getKey()
  if (key) headers['X-Gemini-Key'] = key
  if (json) headers['Content-Type'] = 'application/json'
  let res
  try {
    res = await fetch(path, { method, headers, body: form || (json ? JSON.stringify(json) : undefined) })
  } catch {
    throw new Error('Cannot reach the API. Start it with: uvicorn backend.main:app --port 8000')
  }
  let body
  try { body = await res.json() } catch { throw new Error(`Server error (${res.status})`) }
  if (!res.ok || body.status === 'error') throw new Error(body?.error?.message || `Request failed (${res.status})`)
  return body
}

const upload = (path, file) => {
  const form = new FormData()
  form.append('file', file)
  return request(path, { method: 'POST', form })
}

export const api = {
  health: () => request('/api/health'),
  validateKey: () => request('/api/key/validate', { method: 'POST' }),
  config: () => request('/api/config'),
  safety: (file) => upload('/api/safety/analyze', file),
  cracks: (file) => upload('/api/cracks/analyze', file),
  valuation: (payload) => request('/api/valuation', { method: 'POST', json: payload }),
  renderPrompt: (payload) => request('/api/render-prompt', { method: 'POST', json: payload }),
  advisory: (condition) => request(`/api/weather/advisory/${encodeURIComponent(condition)}`),
  liveWeather: (city) => request(`/api/weather/live?city=${encodeURIComponent(city)}`),
  chat: (messages, context) => request('/api/chat', { method: 'POST', json: { messages, context } }),
}

// ---- formatting helpers
export function formatInr(v) {
  const a = Math.abs(v), s = v < 0 ? '-' : ''
  if (a >= 1e7) return `${s}₹${(a / 1e7).toLocaleString('en-IN', { minimumFractionDigits: 2, maximumFractionDigits: 2 })} Cr`
  if (a >= 1e5) return `${s}₹${(a / 1e5).toLocaleString('en-IN', { minimumFractionDigits: 2, maximumFractionDigits: 2 })} L`
  return `${s}₹${Math.round(a).toLocaleString('en-IN')}`
}
export const num = (v, d = 0) => Number(v).toLocaleString('en-IN', { maximumFractionDigits: d })

export function downloadJson(obj, name) {
  const url = URL.createObjectURL(new Blob([JSON.stringify(obj, null, 2)], { type: 'application/json' }))
  const a = Object.assign(document.createElement('a'), { href: url, download: name })
  a.click()
  URL.revokeObjectURL(url)
}
