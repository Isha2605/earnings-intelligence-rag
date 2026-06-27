import streamlit as st

st.set_page_config(
    page_title="Earnings Intelligence Analyst",
    page_icon="📊",
    layout="wide",
    initial_sidebar_state="collapsed",
)

from components.kpi_dashboard import render as render_dashboard
from components.rag_chatbot import render as render_chatbot

# ── Global style overrides ────────────────────────────────────────────────────
st.markdown("""
<style>
:root {
    --bg: #080D18;
    --panel: #101826;
    --panel-2: #121D2E;
    --panel-3: #17243A;
    --line: rgba(148, 163, 184, 0.18);
    --line-strong: rgba(148, 163, 184, 0.30);
    --text: #F3F7FC;
    --muted: #A7B4C7;
    --faint: #93A4BB;
    --blue: #5B7CFA;
    --navy: #0B1220;
    --cyan: #43C6E8;
    --green: #85D478;
    --amber: #F5BE4F;
    --red: #F16672;
}

/* Hide Streamlit's default header */
header[data-testid="stHeader"] { display: none !important; }
#MainMenu, footer, [data-testid="stToolbar"] { visibility: hidden !important; }

/* Top padding for sticky header */
.main .block-container {
    padding-top: 88px !important;
    padding-bottom: 7rem;
    padding-left: 0 !important;
    padding-right: 0 !important;
    width: 64vw !important;
    max-width: 1228px !important;
    min-width: min(64vw, 100%) !important;
    margin-left: auto !important;
    margin-right: auto !important;
}

/* Page background */
.stApp, [data-testid="stAppViewContainer"] {
    background:
        radial-gradient(circle at 18% 6%, rgba(91,124,250,0.22), transparent 28%),
        radial-gradient(circle at 82% 14%, rgba(67,198,232,0.14), transparent 30%),
        radial-gradient(circle at 50% 96%, rgba(133,212,120,0.08), transparent 34%),
        linear-gradient(180deg, #0A1020 0%, #080D18 42%, #070B14 100%) !important;
    color: var(--text) !important;
}
[data-testid="stAppViewContainer"]::before {
    content: "";
    position: fixed;
    inset: 64px 0 0 0;
    pointer-events: none;
    z-index: 0;
    background-image:
        linear-gradient(rgba(148,163,184,0.09) 1px, transparent 1px),
        linear-gradient(90deg, rgba(148,163,184,0.09) 1px, transparent 1px),
        radial-gradient(circle, rgba(67,198,232,0.30) 1px, transparent 1.7px);
    background-size: 64px 64px, 64px 64px, 28px 28px;
    background-position: -1px -1px, -1px -1px, 0 0;
    opacity: 0.72;
    mask-image: linear-gradient(180deg, rgba(0,0,0,0.94), rgba(0,0,0,0.72) 44%, rgba(0,0,0,0.62) 100%);
}
[data-testid="stAppViewContainer"]::after {
    content: "";
    position: fixed;
    top: 64px;
    left: 0;
    right: 0;
    bottom: 0;
    pointer-events: none;
    z-index: 0;
    background:
        radial-gradient(circle at 78% 45%, rgba(91,124,250,0.20), transparent 30%),
        radial-gradient(circle at 18% 72%, rgba(67,198,232,0.17), transparent 34%),
        linear-gradient(115deg, transparent 0%, rgba(91,124,250,0.13) 38%, transparent 62%),
        linear-gradient(245deg, transparent 0%, rgba(67,198,232,0.10) 42%, transparent 70%);
    opacity: 0.95;
}
[data-testid="stAppViewContainer"] > .main {
    position: relative;
    z-index: 1;
}
[data-testid="stSidebar"] { background-color: var(--panel) !important; }

html, body, .stApp, p, div, span, button, input, textarea {
    font-family: Inter, ui-sans-serif, system-ui, -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif !important;
}

/* Keep Streamlit / Material icons from rendering as raw text. */
span[class*="material-symbols"],
span[class*="material-icons"],
[data-testid="stIconMaterial"] {
    font-family: "Material Symbols Rounded", "Material Icons" !important;
    font-weight: normal !important;
    font-style: normal !important;
    letter-spacing: normal !important;
    text-transform: none !important;
    line-height: 1 !important;
}

/* Tabs */
.stTabs [data-baseweb="tab-list"] {
    background: rgba(16, 24, 38, 0.86);
    border: 1px solid var(--line);
    border-radius: 11px;
    gap: 6px;
    padding: 5px;
    width: fit-content;
    box-shadow: 0 12px 32px rgba(0,0,0,0.22);
}
.stTabs [data-baseweb="tab"] {
    color: var(--muted) !important;
    font-size: 13px;
    font-weight: 700;
    padding: 9px 18px;
    border-radius: 9px;
    transition: all 0.15s;
    border: 0 !important;
}
.stTabs [data-baseweb="tab"]:hover { color: var(--text) !important; background: rgba(255,255,255,0.04); }
.stTabs [aria-selected="true"] {
    color: #FFFFFF !important;
    background: rgba(91,124,250,0.24) !important;
    box-shadow: inset 0 0 0 1px rgba(91,124,250,0.46);
}

/* Buttons (suggested questions) */
.stButton > button {
    background: var(--panel-2) !important;
    color: #D8E3F3 !important;
    border: 1px solid var(--line) !important;
    font-size: 13px !important;
    border-radius: 10px !important;
    min-height: 42px;
    transition: all 0.15s;
    box-shadow: none;
}
.stButton > button:hover {
    background: rgba(91,124,250,0.16) !important;
    color: #FFFFFF !important;
    border-color: rgba(91,124,250,0.48) !important;
    transform: translateY(-1px);
}

/* Selectbox */
[data-baseweb="select"] > div {
    background: var(--panel) !important;
    border-color: var(--line) !important;
    color: var(--text) !important;
}

/* Chat input */
[data-testid="stChatInput"] textarea {
    background: var(--panel) !important;
    border: 1px solid var(--line) !important;
    color: var(--text) !important;
    border-radius: 14px !important;
}
[data-testid="stChatInput"] textarea::placeholder { color: var(--faint) !important; }
[data-testid="stChatInput"] {
    position: fixed !important;
    left: 50% !important;
    bottom: 18px !important;
    transform: translateX(-50%) !important;
    width: min(64vw, 980px) !important;
    z-index: 9998 !important;
    padding: 10px 12px !important;
    border: 1px solid rgba(148,163,184,0.16) !important;
    border-radius: 18px !important;
    background: rgba(8, 13, 24, 0.78) !important;
    backdrop-filter: blur(18px) !important;
    box-shadow: 0 18px 42px rgba(0,0,0,0.34), 0 0 28px rgba(67,198,232,0.08);
}
[data-testid="stChatInput"] > div {
    width: 100% !important;
}

/* Chat messages */
[data-testid="stChatMessage"] {
    background: transparent !important;
    padding: 0.4rem 0 !important;
}
[data-testid="stChatMessageContent"] {
    background: var(--panel) !important;
    color: #D8E3F3 !important;
    border: 1px solid var(--line) !important;
    border-radius: 14px !important;
    padding: 18px 20px !important;
    box-shadow: 0 18px 38px rgba(0,0,0,0.18);
}
[data-testid="stChatMessageContent"] h1,
[data-testid="stChatMessageContent"] h2,
[data-testid="stChatMessageContent"] h3 {
    color: var(--text) !important;
    letter-spacing: 0 !important;
}
[data-testid="stChatMessageContent"] p,
[data-testid="stChatMessageContent"] li {
    color: #D8E3F3 !important;
    line-height: 1.72 !important;
}

/* Expander */
details > summary { color: var(--muted) !important; font-size: 13px; }
[data-testid="stExpander"] {
    background: var(--panel) !important;
    border: 1px solid var(--line) !important;
    border-radius: 12px !important;
}

/* Charts */
[data-testid="stVegaLiteChart"] {
    background: var(--panel);
    border: 1px solid var(--line);
    border-radius: 14px;
    padding: 14px 16px 10px 16px;
    margin-top: 12px;
    box-sizing: border-box;
    max-width: 100%;
    overflow: hidden;
    box-shadow: 0 16px 36px rgba(0,0,0,0.18);
}
[data-testid="stVegaLiteChart"] > div {
    max-width: 100%;
    overflow: hidden;
}
[data-testid="stVegaLiteChart"] canvas,
[data-testid="stVegaLiteChart"] svg {
    max-width: 100% !important;
}

/* Divider */
hr { border-color: var(--line) !important; }

/* Caption / small text */
.stCaption p { color: var(--faint) !important; font-size: 12px; }

/* Spinner */
[data-testid="stSpinner"] div { border-top-color: var(--blue) !important; }

/* Alerts / warnings */
[data-testid="stAlert"] {
    background: rgba(247,201,107,0.10) !important;
    border-color: rgba(247,201,107,0.42) !important;
}

/* General paragraph text */
.stMarkdown p { color: #CBD6E6; font-size: 14px; }

@media (max-width: 900px) {
    .main .block-container {
        padding-left: 1rem !important;
        padding-right: 1rem !important;
        width: 100% !important;
        max-width: 100% !important;
        padding-top: 84px !important;
    }
    [data-testid="stChatInput"] {
        width: calc(100vw - 24px) !important;
        bottom: 12px !important;
    }
    .app-header {
        padding: 0 16px !important;
    }
    .app-header__meta {
        display: none !important;
    }
    .app-header__title {
        font-size: 15px !important;
    }
}
</style>
""", unsafe_allow_html=True)

# ── Sticky header ─────────────────────────────────────────────────────────────
st.markdown("""
<div style="
    position: fixed; top: 0; left: 0; right: 0; z-index: 9999;
    height: 64px;
    background: rgba(9, 15, 28, 0.96);
    backdrop-filter: blur(18px);
    border-bottom: 1px solid rgba(255,255,255,0.08);
    display: flex; align-items: center; justify-content: space-between;
    padding: 0 34px;
    box-shadow: 0 16px 34px rgba(0,0,0,0.28);
" class="app-header">
  <div style="display:flex;align-items:center;gap:14px;">
    <span style="
      width:32px;height:32px;border-radius:10px;display:inline-flex;align-items:center;justify-content:center;
      background:linear-gradient(135deg, #5B7CFA, #43C6E8);
      box-shadow: inset 0 1px 0 rgba(255,255,255,0.35), 0 10px 24px rgba(0,0,0,0.28);
      font-size:17px;line-height:1;">📊</span>
    <span class="app-header__title" style="font-size:17px;font-weight:800;color:#FFFFFF;letter-spacing:0;">
      Microsoft Earnings Intelligence
    </span>
    <span style="
      background: rgba(255,255,255,0.10);
      border: 1px solid rgba(255,255,255,0.18);
      color: #DBEAFE;
      font-size: 10.5px; font-weight: 800;
      padding: 4px 10px; border-radius: 999px;
      letter-spacing: 0.06em; text-transform: uppercase;
    ">FY2022-FY2024</span>
  </div>
  <div class="app-header__meta" style="color:rgba(231,237,247,0.58);font-size:12px;letter-spacing:0.02em;font-weight:650;">
    SEC 10-K Filings &nbsp;·&nbsp; RAG + Claude Sonnet
  </div>
</div>
""", unsafe_allow_html=True)

tab1, tab2 = st.tabs(["📊  KPI Dashboard", "💬  Ask the Filings"])

with tab1:
    render_dashboard()

with tab2:
    render_chatbot()
