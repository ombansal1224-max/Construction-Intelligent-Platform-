"""Global CSS: dark construction-tech glassmorphism theme."""

CSS = """
@import url('https://fonts.googleapis.com/css2?family=Outfit:wght@300;400;500;600;700;800&family=Inter:wght@400;500;600&display=swap');

:root {
  --bg: #080d1a;
  --panel: rgba(255,255,255,0.045);
  --panel-strong: rgba(255,255,255,0.075);
  --border: rgba(255,255,255,0.10);
  --text: #e8ecf5;
  --muted: #94a0b8;
  --amber: #ffb020;
  --orange: #ff7a1a;
  --cyan: #22d3ee;
  --green: #34d399;
  --red: #fb5470;
  --violet: #a78bfa;
}

html, body, [class*="css"], .stApp { font-family: 'Inter', sans-serif; }
h1, h2, h3, h4, .hero-title, .metric-value, .section-title { font-family: 'Outfit', sans-serif !important; letter-spacing: -0.01em; }

.stApp {
  background:
    radial-gradient(1100px 600px at 8% -10%, rgba(255,176,32,0.14), transparent 60%),
    radial-gradient(900px 520px at 100% 0%, rgba(34,211,238,0.12), transparent 55%),
    radial-gradient(800px 600px at 50% 120%, rgba(167,139,250,0.10), transparent 60%),
    var(--bg);
}
#MainMenu, footer { visibility: hidden; }
header[data-testid="stHeader"] { background: transparent; }
.block-container { padding-top: 1.4rem; max-width: 1280px; }

/* ---------- sidebar ---------- */
[data-testid="stSidebar"] {
  background: linear-gradient(180deg, rgba(16,22,40,0.98), rgba(10,14,28,0.98));
  border-right: 1px solid var(--border);
}
.brand { display:flex; align-items:center; gap:.7rem; margin-bottom:.6rem; }
.brand-logo {
  width:44px; height:44px; border-radius:12px; display:grid; place-items:center; font-size:1.5rem;
  background: linear-gradient(135deg, var(--amber), var(--orange)); box-shadow: 0 8px 24px rgba(255,122,26,.35);
}
.brand-name { font-family:'Outfit'; font-weight:700; font-size:1.05rem; line-height:1.15; }
.brand-sub { color: var(--muted); font-size:.72rem; }

/* ---------- hero ---------- */
.hero {
  position:relative; overflow:hidden; border-radius:22px; padding:1.9rem 2.1rem; margin-bottom:1.2rem;
  background: linear-gradient(120deg, rgba(255,176,32,0.16), rgba(255,122,26,0.06) 40%, rgba(34,211,238,0.10));
  border:1px solid var(--border); backdrop-filter: blur(14px);
}
.hero::after {
  content:""; position:absolute; right:-60px; top:-60px; width:260px; height:260px; border-radius:50%;
  background: radial-gradient(circle, rgba(255,176,32,.35), transparent 70%); filter: blur(10px);
  animation: float 7s ease-in-out infinite;
}
@keyframes float { 0%,100% { transform: translateY(0); } 50% { transform: translateY(18px); } }
.hero-kicker { color: var(--amber); font-weight:600; letter-spacing:.14em; font-size:.74rem; text-transform:uppercase; }
.hero-title { font-size:2.35rem; font-weight:800; margin:.2rem 0 .35rem; line-height:1.1;
  background: linear-gradient(90deg,#fff,#ffd98a 60%,#7fe7f7); -webkit-background-clip:text; background-clip:text; color:transparent; }
.hero-sub { color: var(--muted); max-width: 760px; font-size:.98rem; }

/* ---------- cards ---------- */
.card {
  background: var(--panel); border:1px solid var(--border); border-radius:16px; padding:1rem 1.15rem;
  backdrop-filter: blur(10px); transition: transform .2s ease, border-color .2s ease, box-shadow .2s ease; height:100%;
}
.card:hover { transform: translateY(-3px); border-color: rgba(255,176,32,.45); box-shadow: 0 14px 34px rgba(0,0,0,.35); }
.metric-label { color: var(--muted); font-size:.74rem; text-transform:uppercase; letter-spacing:.09em; font-weight:600; }
.metric-value { font-size:1.65rem; font-weight:700; margin:.15rem 0; }
.metric-sub { color: var(--muted); font-size:.8rem; }
.accent-amber .metric-value { color: var(--amber); }
.accent-cyan .metric-value { color: var(--cyan); }
.accent-green .metric-value { color: var(--green); }
.accent-red .metric-value { color: var(--red); }
.accent-violet .metric-value { color: var(--violet); }

.section-title { font-size:1.35rem; font-weight:700; margin:.4rem 0 .15rem; }
.section-sub { color: var(--muted); margin-bottom:.9rem; font-size:.92rem; }
.subhead { font-family:'Outfit'; font-weight:600; font-size:1.05rem; margin:1.1rem 0 .5rem; color:#fff; }

/* ---------- pills ---------- */
.pill { display:inline-block; padding:.2rem .65rem; border-radius:999px; font-size:.72rem; font-weight:700;
  letter-spacing:.04em; border:1px solid transparent; white-space:nowrap; }
.pill-ok   { background:rgba(52,211,153,.14); color:#6ee7b7; border-color:rgba(52,211,153,.4); }
.pill-warn { background:rgba(255,176,32,.14); color:#ffd37a; border-color:rgba(255,176,32,.4); }
.pill-bad  { background:rgba(255,122,26,.16); color:#ffa56b; border-color:rgba(255,122,26,.45); }
.pill-crit { background:rgba(251,84,112,.16); color:#ff8da1; border-color:rgba(251,84,112,.5); }
.pill-info { background:rgba(34,211,238,.13); color:#7fe7f7; border-color:rgba(34,211,238,.4); }
.pill-muted{ background:rgba(148,160,184,.12); color:#b4bed3; border-color:rgba(148,160,184,.3); }
.pill-live { animation: pulse 2s infinite; }
@keyframes pulse { 0%{box-shadow:0 0 0 0 rgba(52,211,153,.5);} 70%{box-shadow:0 0 0 9px rgba(52,211,153,0);} 100%{box-shadow:0 0 0 0 rgba(52,211,153,0);} }

/* ---------- score ring ---------- */
.ring-wrap { display:flex; flex-direction:column; align-items:center; gap:.5rem; }
.ring { --p:0; --c: var(--green); width:150px; height:150px; border-radius:50%; display:grid; place-items:center;
  background: conic-gradient(var(--c) calc(var(--p) * 1%), rgba(255,255,255,0.08) 0); position:relative;
  box-shadow: 0 0 40px color-mix(in srgb, var(--c) 30%, transparent); }
.ring::before { content:""; position:absolute; inset:12px; border-radius:50%; background:#0d1424; }
.ring-num { position:relative; font-family:'Outfit'; font-size:2.5rem; font-weight:800; line-height:1; text-align:center; }
.ring-num small { display:block; font-size:.7rem; color:var(--muted); font-weight:500; letter-spacing:.1em; margin-top:.2rem; }

/* ---------- ppe / hazard / steps ---------- */
.ppe-icon { font-size:1.7rem; }
.ppe-label { font-weight:600; margin:.25rem 0; }
.ppe-note { color:var(--muted); font-size:.76rem; margin-top:.4rem; }
.bar { height:6px; border-radius:99px; background:rgba(255,255,255,.08); overflow:hidden; margin-top:.4rem; }
.bar > span { display:block; height:100%; border-radius:99px; background: linear-gradient(90deg,var(--amber),var(--orange)); }
.hazard { border-left:4px solid var(--amber); }
.hazard.sev-Critical { border-left-color: var(--red); } .hazard.sev-High { border-left-color: var(--orange); }
.hazard.sev-Medium { border-left-color: var(--amber); } .hazard.sev-Low { border-left-color: var(--cyan); }
.hazard-title { font-weight:600; margin-bottom:.3rem; }
.hazard-meta { color:var(--muted); font-size:.78rem; margin-bottom:.4rem; }
.remedy { font-size:.88rem; }
.remedy b { color: var(--green); }
.step { display:flex; gap:.8rem; align-items:flex-start; }
.step-num { min-width:30px; height:30px; border-radius:50%; display:grid; place-items:center; font-weight:700;
  background:linear-gradient(135deg,var(--amber),var(--orange)); color:#1a1205; }
.callout { border-radius:12px; padding:.75rem 1rem; font-size:.9rem; margin:.5rem 0 1rem; border:1px solid var(--border); background: var(--panel); }
.callout-info { border-color: rgba(34,211,238,.4); background: rgba(34,211,238,.07); }
.callout-warn { border-color: rgba(255,176,32,.45); background: rgba(255,176,32,.08); }

/* ---------- ops grid ---------- */
.op { display:flex; justify-content:space-between; align-items:center; gap:.6rem; }
.op-name { font-weight:600; font-size:.92rem; }
.op-note { color:var(--muted); font-size:.78rem; margin-top:.3rem; }

/* ---------- milestones ---------- */
.ms-row { margin:.55rem 0; }
.ms-head { display:flex; justify-content:space-between; font-size:.88rem; margin-bottom:.25rem; gap:.5rem; }

.render-frame { border-radius:18px; overflow:hidden; border:1px solid var(--border); background:var(--panel);
  box-shadow:0 20px 50px rgba(0,0,0,.4); }
.render-frame img { width:100%; display:block; }

/* ---------- streamlit widget polish ---------- */
.stTabs [data-baseweb="tab-list"] { gap:.4rem; background: var(--panel); padding:.35rem; border-radius:14px; border:1px solid var(--border); }
.stTabs [data-baseweb="tab"] { height:2.7rem; border-radius:10px; padding:0 1.1rem; font-weight:600; color: var(--muted); }
.stTabs [aria-selected="true"] { background: linear-gradient(135deg, rgba(255,176,32,.25), rgba(255,122,26,.18)); color:#fff !important; }
.stTabs [data-baseweb="tab-highlight"], .stTabs [data-baseweb="tab-border"] { display:none; }
.stButton > button, .stDownloadButton > button {
  border-radius:12px; font-weight:600; border:1px solid var(--border); transition: all .2s ease; }
.stButton > button[kind="primary"] {
  background: linear-gradient(135deg, var(--amber), var(--orange)); color:#1a1205; border:none;
  box-shadow: 0 8px 22px rgba(255,122,26,.3); }
.stButton > button:hover, .stDownloadButton > button:hover { transform: translateY(-2px); border-color: var(--amber); }
[data-testid="stFileUploader"] section { border:2px dashed rgba(255,176,32,.4); border-radius:16px; background: var(--panel); }
[data-testid="stChatMessage"] { background: var(--panel); border:1px solid var(--border); border-radius:14px; }
[data-testid="stExpander"] { border:1px solid var(--border); border-radius:14px; background: var(--panel); }
"""
