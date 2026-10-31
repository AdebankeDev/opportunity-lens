"""
app.py — OpportunityLens Streamlit application.
Redesigned frontend — investor-demo quality SaaS/EdTech UI.

Run with:
    streamlit run app.py
"""

from __future__ import annotations
import html
import os
import uuid
from pathlib import Path
from typing import Optional

import streamlit as st

# ── Load .env using an explicit path relative to this file ────────────────────
ENV_PATH = Path(__file__).resolve().parent / ".env"
try:
    from dotenv import load_dotenv
    if ENV_PATH.exists():
        load_dotenv(dotenv_path=ENV_PATH, override=True)
except ImportError:
    pass

# ── Load Streamlit Community Cloud secrets ────────────────────────────────────
try:
    if hasattr(st, "secrets"):
        if "GEMINI_API_KEY" in st.secrets and st.secrets["GEMINI_API_KEY"]:
            os.environ["GEMINI_API_KEY"] = str(st.secrets["GEMINI_API_KEY"]).strip()
        elif "GOOGLE_API_KEY" in st.secrets and st.secrets["GOOGLE_API_KEY"]:
            os.environ["GEMINI_API_KEY"] = str(st.secrets["GOOGLE_API_KEY"]).strip()
except Exception:
    pass

from schemas import StudentProfile, ExtractedOpportunity, EligibilityAssessment, ChecklistItem
from document_processor import extract_text_from_pdf, validate_pasted_text
from eligibility_engine import run_eligibility_check
import gemma_service

# ─────────────────────────────────────────────────────────────────────────────
# PAGE CONFIG
# ─────────────────────────────────────────────────────────────────────────────

st.set_page_config(
    page_title="OpportunityLens",
    page_icon="🔍",
    layout="wide",
    initial_sidebar_state="expanded",
)

def render_html(html_str: str):
    """
    Safely render HTML snippets directly to DOM without Markdown-it parser
    converting indented HTML tags or blank lines into raw <pre><code> blocks.
    """
    clean = "\n".join(line.strip() for line in html_str.strip().splitlines() if line.strip())
    if hasattr(st, "html"):
        st.html(clean)
    else:
        st.markdown(clean, unsafe_allow_html=True)

# ─────────────────────────────────────────────────────────────────────────────
# DESIGN TOKENS
# ─────────────────────────────────────────────────────────────────────────────

NAV_BG      = "#0c1526"   # sidebar background
NAVY        = "#0f172a"   # primary text / headings
NAVY_MID    = "#1e293b"   # secondary dark
SLATE       = "#475569"   # muted text
SLATE_LT    = "#94a3b8"   # placeholder / subtle
GREEN       = "#16a34a"   # primary accent (buttons, MET)
GREEN_LT    = "#dcfce7"   # green tint background
GREEN_TEXT  = "#15803d"   # green text on tint
AMBER       = "#d97706"
AMBER_LT    = "#fef3c7"
AMBER_TEXT  = "#92400e"
RED         = "#dc2626"
RED_LT      = "#fee2e2"
RED_TEXT    = "#b91c1c"
SURFACE     = "#ffffff"   # card background
BG          = "#f1f5f9"   # page background
BORDER      = "#e2e8f0"   # subtle border
BORDER_MID  = "#cbd5e1"

# ─────────────────────────────────────────────────────────────────────────────
# CSS
# ─────────────────────────────────────────────────────────────────────────────

CUSTOM_CSS = f"""
<style>
/* ── Web font ── */
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700;800&display=swap');

/* ── Reset Streamlit defaults ── */
html, body, [class*="css"] {{
    font-family: 'Inter', -apple-system, BlinkMacSystemFont, sans-serif;
}}

/* ── Hide toolbar / footer / deploy button ── */
#MainMenu, footer, header,
[data-testid="stToolbar"],
[data-testid="stDecoration"],
.reportview-container .main footer {{
    visibility: hidden;
    height: 0;
}}

/* ── Page background ── */
.stApp {{
    background: {BG};
}}

/* ── Main content padding ── */
.block-container {{
    padding-top: 2rem !important;
    padding-bottom: 3rem !important;
    max-width: 1100px;
}}

/* ═══════════════════════════════════════════════════════════════
   SIDEBAR
═══════════════════════════════════════════════════════════════ */
[data-testid="stSidebar"] {{
    background: {NAV_BG} !important;
    border-right: 1px solid #1a2740 !important;
}}
[data-testid="stSidebar"] > div:first-child {{
    padding-top: 0 !important;
}}
/* Kill default sidebar header padding */
[data-testid="stSidebarContent"] {{
    padding: 0 !important;
}}

/* ── Sidebar nav buttons ── */
[data-testid="stSidebar"] .stButton > button {{
    width: 100%;
    text-align: left !important;
    justify-content: flex-start !important;
    border: none !important;
    border-radius: 8px !important;
    padding: 0.55rem 1rem !important;
    font-size: 0.88rem !important;
    font-weight: 500 !important;
    color: {SLATE_LT} !important;
    background: transparent !important;
    transition: background 0.15s, color 0.15s;
    margin: 1px 0 !important;
}}
[data-testid="stSidebar"] .stButton > button:hover {{
    background: rgba(255,255,255,0.06) !important;
    color: #e2e8f0 !important;
}}
[data-testid="stSidebar"] .stButton > button[kind="primary"] {{
    background: rgba(22, 163, 74, 0.15) !important;
    color: #4ade80 !important;
    border-left: 3px solid {GREEN} !important;
    border-radius: 0 8px 8px 0 !important;
    padding-left: calc(1rem - 3px) !important;
}}

/* ═══════════════════════════════════════════════════════════════
   TYPOGRAPHY
═══════════════════════════════════════════════════════════════ */
h1, h2, h3, h4 {{
    color: {NAVY} !important;
    font-family: 'Inter', sans-serif !important;
    letter-spacing: -0.02em;
}}

/* ═══════════════════════════════════════════════════════════════
   CARDS
═══════════════════════════════════════════════════════════════ */
.ol-card {{
    background: {SURFACE};
    border: 1px solid {BORDER};
    border-radius: 12px;
    padding: 1.5rem 1.75rem;
    margin-bottom: 1rem;
    box-shadow: 0 1px 4px rgba(15,23,42,0.05);
}}
.ol-card-sm {{
    background: {SURFACE};
    border: 1px solid {BORDER};
    border-radius: 10px;
    padding: 1.1rem 1.25rem;
    margin-bottom: 0.6rem;
    box-shadow: 0 1px 2px rgba(15,23,42,0.04);
}}
.ol-card-title {{
    font-size: 0.78rem;
    font-weight: 700;
    letter-spacing: 0.07em;
    text-transform: uppercase;
    color: {SLATE};
    margin-bottom: 0.35rem;
}}
.ol-card-value {{
    font-size: 1.45rem;
    font-weight: 700;
    color: {NAVY};
    line-height: 1.2;
}}

/* ═══════════════════════════════════════════════════════════════
   HERO
═══════════════════════════════════════════════════════════════ */
.ol-hero {{
    background: {SURFACE};
    border: 1px solid {BORDER};
    border-radius: 14px;
    padding: 2.25rem 2.5rem;
    margin-bottom: 1.75rem;
    box-shadow: 0 2px 8px rgba(15,23,42,0.06);
    position: relative;
    overflow: hidden;
}}
.ol-hero::before {{
    content: '';
    position: absolute;
    top: 0; left: 0;
    width: 4px; height: 100%;
    background: {GREEN};
    border-radius: 14px 0 0 14px;
}}
.ol-hero-logo {{
    font-size: 1.75rem;
    font-weight: 800;
    color: {NAVY};
    letter-spacing: -0.03em;
    line-height: 1;
    margin-bottom: 0.35rem;
}}
.ol-hero-logo span {{
    color: {GREEN};
}}
.ol-hero-tag {{
    font-size: 0.9rem;
    color: {SLATE};
    font-weight: 400;
    margin-bottom: 1.25rem;
}}
.ol-hero-cta {{
    display: inline-flex;
    align-items: center;
    gap: 0.4rem;
    font-size: 0.82rem;
    font-weight: 600;
    letter-spacing: 0.04em;
    text-transform: uppercase;
    color: {GREEN};
}}

/* ═══════════════════════════════════════════════════════════════
   FEATURE STRIP
═══════════════════════════════════════════════════════════════ */
.ol-feature {{
    background: {SURFACE};
    border: 1px solid {BORDER};
    border-radius: 10px;
    padding: 1.2rem 1.3rem;
    height: 100%;
}}
.ol-feature-icon {{
    font-size: 1.4rem;
    margin-bottom: 0.5rem;
}}
.ol-feature-title {{
    font-size: 0.9rem;
    font-weight: 700;
    color: {NAVY};
    margin-bottom: 0.3rem;
}}
.ol-feature-body {{
    font-size: 0.83rem;
    color: {SLATE};
    line-height: 1.5;
}}

/* ═══════════════════════════════════════════════════════════════
   STEP TRACKER
═══════════════════════════════════════════════════════════════ */
.ol-step {{
    display: flex;
    align-items: center;
    gap: 0.9rem;
    padding: 0.7rem 0;
    border-bottom: 1px solid {BG};
}}
.ol-step-num {{
    width: 28px; height: 28px;
    border-radius: 50%;
    display: flex; align-items: center; justify-content: center;
    font-size: 0.72rem;
    font-weight: 700;
    flex-shrink: 0;
}}
.ol-step-num.done {{ background: {GREEN_LT}; color: {GREEN_TEXT}; }}
.ol-step-num.todo {{ background: {BG}; color: {SLATE}; border: 1.5px solid {BORDER_MID}; }}
.ol-step-label {{ font-weight: 600; color: {NAVY}; font-size: 0.9rem; }}
.ol-step-desc  {{ font-size: 0.81rem; color: {SLATE}; }}

/* ═══════════════════════════════════════════════════════════════
   SECTION HEADERS
═══════════════════════════════════════════════════════════════ */
.ol-page-header {{
    margin-bottom: 1.5rem;
}}
.ol-page-title {{
    font-size: 1.45rem;
    font-weight: 800;
    color: {NAVY};
    letter-spacing: -0.02em;
    margin-bottom: 0.2rem;
}}
.ol-page-sub {{
    font-size: 0.88rem;
    color: {SLATE};
}}
.ol-section-label {{
    font-size: 0.75rem;
    font-weight: 700;
    letter-spacing: 0.07em;
    text-transform: uppercase;
    color: {SLATE};
    margin-bottom: 0.6rem;
    margin-top: 1.4rem;
    display: flex;
    align-items: center;
    gap: 0.4rem;
}}
.ol-section-label::after {{
    content: '';
    flex: 1;
    height: 1px;
    background: {BORDER};
    margin-left: 0.5rem;
}}
.ol-divider {{
    height: 1px;
    background: {BORDER};
    margin: 1.5rem 0;
}}

/* ═══════════════════════════════════════════════════════════════
   STATUS BADGES
═══════════════════════════════════════════════════════════════ */
.ol-badge {{
    display: inline-flex;
    align-items: center;
    gap: 0.3rem;
    padding: 3px 10px 3px 8px;
    border-radius: 20px;
    font-size: 0.72rem;
    font-weight: 700;
    text-transform: uppercase;
    letter-spacing: 0.05em;
    white-space: nowrap;
}}
.ol-badge-met    {{ background: {GREEN_LT}; color: {GREEN_TEXT}; }}
.ol-badge-notmet {{ background: {RED_LT};   color: {RED_TEXT};   }}
.ol-badge-verify {{ background: {AMBER_LT}; color: {AMBER_TEXT}; }}
.ol-badge-na     {{ background: #f1f5f9;    color: {SLATE};      }}

/* ═══════════════════════════════════════════════════════════════
   ASSESSMENT BANNER
═══════════════════════════════════════════════════════════════ */
.ol-assess-banner {{
    border-radius: 12px;
    padding: 1.5rem 1.75rem;
    margin-bottom: 1.25rem;
    display: flex;
    align-items: flex-start;
    gap: 1.25rem;
}}
.ol-assess-icon {{
    font-size: 2.2rem;
    line-height: 1;
    flex-shrink: 0;
}}
.ol-assess-status {{
    font-size: 1.15rem;
    font-weight: 800;
    letter-spacing: -0.01em;
    margin-bottom: 0.25rem;
}}
.ol-assess-body {{ font-size: 0.9rem; line-height: 1.55; }}

.ol-assess-eligible    {{ background:{GREEN_LT}; border:1.5px solid #bbf7d0; }}
.ol-assess-potential   {{ background:{AMBER_LT}; border:1.5px solid #fde68a; }}
.ol-assess-ineligible  {{ background:{RED_LT};   border:1.5px solid #fecaca; }}
.ol-assess-insufficient{{ background:#f1f5f9;    border:1.5px solid {BORDER_MID}; }}

/* ═══════════════════════════════════════════════════════════════
   STAT PILLS (metrics row)
═══════════════════════════════════════════════════════════════ */
.ol-stat {{
    background: {SURFACE};
    border: 1px solid {BORDER};
    border-radius: 10px;
    padding: 0.9rem 1rem;
    text-align: center;
}}
.ol-stat-num   {{ font-size: 1.9rem; font-weight: 800; line-height: 1; }}
.ol-stat-label {{ font-size: 0.7rem; font-weight: 600; letter-spacing: 0.06em;
                  text-transform: uppercase; color: {SLATE}; margin-top: 0.2rem; }}

/* ═══════════════════════════════════════════════════════════════
   REQUIREMENT ROW CARDS
═══════════════════════════════════════════════════════════════ */
.ol-req-card {{
    background: {SURFACE};
    border: 1px solid {BORDER};
    border-radius: 10px;
    padding: 0.9rem 1.1rem 0.9rem 1rem;
    margin-bottom: 0.5rem;
    display: flex;
    align-items: flex-start;
    gap: 0.9rem;
    transition: box-shadow 0.15s;
}}
.ol-req-card:hover {{ box-shadow: 0 2px 8px rgba(15,23,42,0.07); }}
.ol-req-card-notmet  {{ border-left: 3px solid {RED}; }}
.ol-req-card-met     {{ border-left: 3px solid {GREEN}; }}
.ol-req-card-verify  {{ border-left: 3px solid {AMBER}; }}
.ol-req-card-na      {{ border-left: 3px solid {BORDER_MID}; }}
.ol-req-name  {{ font-size: 0.88rem; font-weight: 600; color: {NAVY}; }}
.ol-req-expl  {{ font-size: 0.82rem; color: {SLATE}; margin-top: 0.2rem; line-height: 1.45; }}
.ol-req-vals  {{ font-size: 0.78rem; color: {SLATE_LT}; margin-top: 0.3rem; }}
.ol-req-vals strong {{ color: {SLATE}; }}

/* ═══════════════════════════════════════════════════════════════
   SOURCE EXCERPT
═══════════════════════════════════════════════════════════════ */
.ol-excerpt {{
    background: #f8fafc;
    border-left: 3px solid #22c55e;
    padding: 0.45rem 0.75rem;
    font-size: 0.8rem;
    color: {SLATE};
    border-radius: 0 6px 6px 0;
    font-style: italic;
    margin-top: 0.5rem;
}}

/* ═══════════════════════════════════════════════════════════════
   CHECKLIST
═══════════════════════════════════════════════════════════════ */
.ol-cl-header {{
    background: {SURFACE};
    border: 1px solid {BORDER};
    border-radius: 12px;
    padding: 1.25rem 1.5rem;
    margin-bottom: 1.25rem;
    box-shadow: 0 1px 4px rgba(15,23,42,0.05);
}}
.ol-cl-title {{
    font-size: 1.05rem;
    font-weight: 700;
    color: {NAVY};
    margin-bottom: 0.3rem;
}}
.ol-cl-meta {{
    font-size: 0.82rem;
    color: {SLATE};
    margin-bottom: 0.75rem;
}}
.ol-cl-progress-bar {{
    height: 6px;
    background: {BORDER};
    border-radius: 3px;
    overflow: hidden;
    margin-top: 0.5rem;
}}
.ol-cl-progress-fill {{
    height: 100%;
    background: {GREEN};
    border-radius: 3px;
    transition: width 0.3s;
}}
.ol-cl-section {{
    font-size: 0.73rem;
    font-weight: 700;
    letter-spacing: 0.07em;
    text-transform: uppercase;
    color: {SLATE};
    padding: 0.5rem 0 0.4rem;
    margin-top: 0.75rem;
    border-bottom: 1px solid {BORDER};
    margin-bottom: 0.4rem;
}}
.ol-cl-item {{
    display: flex;
    align-items: flex-start;
    gap: 0.75rem;
    background: {SURFACE};
    border: 1px solid {BORDER};
    border-radius: 8px;
    padding: 0.65rem 0.9rem;
    margin-bottom: 0.4rem;
}}
.ol-cl-item.done {{
    background: #fafafa;
    border-color: #f1f5f9;
}}
.ol-cl-item-text {{
    font-size: 0.86rem;
    font-weight: 500;
    color: {NAVY};
    line-height: 1.4;
}}
.ol-cl-item-text.done {{
    color: {SLATE_LT};
    text-decoration: line-through;
}}
.ol-cl-item-detail {{
    font-size: 0.77rem;
    color: {SLATE_LT};
    margin-top: 0.15rem;
}}
.ol-cl-cat-chip {{
    display: inline-block;
    padding: 2px 8px;
    border-radius: 20px;
    font-size: 0.68rem;
    font-weight: 600;
    text-transform: uppercase;
    letter-spacing: 0.05em;
    flex-shrink: 0;
    margin-top: 2px;
}}
.chip-doc    {{ background: #eff6ff; color: #1d4ed8; }}
.chip-verify {{ background: {AMBER_LT}; color: {AMBER_TEXT}; }}
.chip-action {{ background: #f0fdf4; color: {GREEN_TEXT}; }}

/* ═══════════════════════════════════════════════════════════════
   DEMO PILL
═══════════════════════════════════════════════════════════════ */
.ol-demo-pill {{
    display: inline-flex;
    align-items: center;
    gap: 0.35rem;
    background: #eff6ff;
    border: 1px solid #bfdbfe;
    color: #1d4ed8;
    border-radius: 20px;
    padding: 0.3rem 0.85rem;
    font-size: 0.75rem;
    font-weight: 600;
    letter-spacing: 0.04em;
    text-transform: uppercase;
    margin-bottom: 0.6rem;
}}

/* ═══════════════════════════════════════════════════════════════
   DISCLAIMER
═══════════════════════════════════════════════════════════════ */
.ol-disclaimer {{
    background: #fffbeb;
    border: 1px solid #fde68a;
    border-radius: 8px;
    padding: 0.75rem 1rem;
    font-size: 0.82rem;
    color: {AMBER_TEXT};
    margin-top: 1.25rem;
    display: flex;
    gap: 0.5rem;
    align-items: flex-start;
}}

/* ═══════════════════════════════════════════════════════════════
   EMPTY STATE
═══════════════════════════════════════════════════════════════ */
.ol-empty {{
    text-align: center;
    padding: 4rem 1rem;
    color: {SLATE_LT};
}}
.ol-empty-icon {{ font-size: 2.5rem; margin-bottom: 0.75rem; opacity: 0.5; }}
.ol-empty-title {{ font-size: 1.05rem; font-weight: 600; color: {SLATE}; margin-bottom: 0.4rem; }}
.ol-empty-body  {{ font-size: 0.88rem; color: {SLATE_LT}; }}

/* ═══════════════════════════════════════════════════════════════
   OPPORTUNITY OVERVIEW CARD
═══════════════════════════════════════════════════════════════ */
.ol-opp-card {{
    background: {SURFACE};
    border: 1px solid {BORDER};
    border-radius: 12px;
    padding: 1.5rem 1.75rem;
    margin-bottom: 1.25rem;
    box-shadow: 0 1px 4px rgba(15,23,42,0.05);
}}
.ol-opp-title {{
    font-size: 1.2rem;
    font-weight: 800;
    color: {NAVY};
    letter-spacing: -0.02em;
    margin-bottom: 0.2rem;
}}
.ol-opp-org {{
    font-size: 0.88rem;
    color: {SLATE};
    margin-bottom: 1rem;
}}
.ol-opp-pill {{
    display: inline-block;
    padding: 3px 10px;
    border-radius: 20px;
    font-size: 0.72rem;
    font-weight: 600;
    text-transform: uppercase;
    letter-spacing: 0.04em;
    background: #f0fdf4;
    color: {GREEN_TEXT};
    border: 1px solid #bbf7d0;
    margin-right: 0.4rem;
}}
.ol-opp-meta-row {{
    display: flex;
    flex-wrap: wrap;
    gap: 1.5rem;
    margin-top: 1rem;
    padding-top: 1rem;
    border-top: 1px solid {BORDER};
}}
.ol-opp-meta-item {{
    display: flex;
    flex-direction: column;
    gap: 0.1rem;
}}
.ol-opp-meta-key {{
    font-size: 0.7rem;
    font-weight: 600;
    letter-spacing: 0.06em;
    text-transform: uppercase;
    color: {SLATE_LT};
}}
.ol-opp-meta-val {{
    font-size: 0.88rem;
    font-weight: 500;
    color: {NAVY};
}}

/* ═══════════════════════════════════════════════════════════════
   UPLOAD ZONE
═══════════════════════════════════════════════════════════════ */
.ol-upload-zone {{
    background: {SURFACE};
    border: 2px dashed {BORDER_MID};
    border-radius: 12px;
    padding: 2rem 1.5rem;
    text-align: center;
    transition: border-color 0.2s;
}}
.ol-upload-zone:hover {{ border-color: {GREEN}; }}

/* ═══════════════════════════════════════════════════════════════
   BUTTONS — global override
═══════════════════════════════════════════════════════════════ */
.stButton > button[kind="primary"] {{
    background: {GREEN} !important;
    color: white !important;
    border: none !important;
    border-radius: 8px !important;
    font-weight: 600 !important;
    font-size: 0.88rem !important;
    padding: 0.55rem 1.3rem !important;
    transition: background 0.2s, box-shadow 0.2s !important;
    box-shadow: 0 1px 3px rgba(22,163,74,0.3) !important;
}}
.stButton > button[kind="primary"]:hover {{
    background: #15803d !important;
    box-shadow: 0 2px 6px rgba(22,163,74,0.4) !important;
}}
.stButton > button[kind="secondary"] {{
    background: {SURFACE} !important;
    color: {NAVY} !important;
    border: 1px solid {BORDER_MID} !important;
    border-radius: 8px !important;
    font-weight: 500 !important;
    font-size: 0.88rem !important;
    padding: 0.55rem 1.3rem !important;
}}
.stButton > button[kind="secondary"]:hover {{
    background: {BG} !important;
    border-color: {SLATE} !important;
}}

/* ── Form submit ── */
[data-testid="stFormSubmitButton"] > button {{
    background: {GREEN} !important;
    color: white !important;
    border: none !important;
    border-radius: 8px !important;
    font-weight: 600 !important;
    font-size: 0.9rem !important;
    padding: 0.6rem 1.5rem !important;
    box-shadow: 0 1px 3px rgba(22,163,74,0.3) !important;
    width: 100% !important;
}}
[data-testid="stFormSubmitButton"] > button:hover {{
    background: #15803d !important;
}}

/* ── Inputs ── */
.stTextInput input, .stTextArea textarea, .stSelectbox select {{
    border-radius: 8px !important;
    border: 1px solid {BORDER_MID} !important;
    font-size: 0.9rem !important;
    color: {NAVY} !important;
}}
.stTextInput input:focus, .stTextArea textarea:focus {{
    border-color: {GREEN} !important;
    box-shadow: 0 0 0 3px rgba(22,163,74,0.12) !important;
}}

/* ── Tabs ── */
.stTabs [data-baseweb="tab-list"] {{
    background: transparent !important;
    gap: 0.25rem;
    border-bottom: 2px solid {BORDER};
}}
.stTabs [data-baseweb="tab"] {{
    background: transparent !important;
    border: none !important;
    font-size: 0.85rem !important;
    font-weight: 500 !important;
    color: {SLATE} !important;
    padding: 0.55rem 1rem !important;
    border-radius: 6px 6px 0 0 !important;
}}
.stTabs [aria-selected="true"] {{
    color: {NAVY} !important;
    font-weight: 700 !important;
    border-bottom: 2.5px solid {GREEN} !important;
}}

/* ── Expanders ── */
[data-testid="stExpander"] {{
    border: 1px solid {BORDER} !important;
    border-radius: 10px !important;
    background: {SURFACE} !important;
    margin-bottom: 0.5rem;
}}
[data-testid="stExpander"] summary {{
    font-weight: 600 !important;
    color: {NAVY} !important;
    font-size: 0.9rem !important;
}}

/* ── Progress bar ── */
.stProgress > div > div {{ background: {GREEN} !important; }}

/* ── Info / success / warning / error boxes ── */
.stAlert {{ border-radius: 8px !important; font-size: 0.88rem !important; }}

/* ── Spinner text ── */
.stSpinner > div {{ color: {SLATE} !important; }}

/* ── Checkbox ── */
.stCheckbox input[type="checkbox"]:checked {{ accent-color: {GREEN}; }}

/* ── Sidebar divider ── */
[data-testid="stSidebar"] hr {{
    border-color: #1a2740 !important;
    margin: 0.75rem 0 !important;
}}
</style>
"""

# ─────────────────────────────────────────────────────────────────────────────
# SAMPLE OPPORTUNITY
# ─────────────────────────────────────────────────────────────────────────────

SAMPLE_OPPORTUNITY_TEXT = """
ILLUSTRATIVE SAMPLE — NOT A REAL SCHOLARSHIP

NORTHGATE UNIVERSITY GLOBAL EXCELLENCE FELLOWSHIP 2025
(This is a fictional sample created solely for demonstrating OpportunityLens.)

ABOUT THE FELLOWSHIP
The Northgate University Global Excellence Fellowship is a prestigious postgraduate funding programme
designed to support outstanding international students from developing nations who wish to pursue a
Master's or PhD degree at Northgate University's Graduate School of Science and Technology.

ELIGIBLE COUNTRIES
Applications are open to citizens of: Nigeria, Ghana, Kenya, Ethiopia, Rwanda, Uganda, Tanzania,
Cameroon, Senegal, Côte d'Ivoire, South Africa, Egypt, Morocco, Bangladesh, Pakistan, Sri Lanka,
Nepal, Myanmar, Cambodia, Laos, Bolivia, Ecuador, Paraguay, Honduras, and Guatemala.

ACADEMIC REQUIREMENTS
- Current enrolment in or application to a Master's or PhD programme at Northgate University.
- Academic level: Postgraduate (Masters or PhD).
- Eligible disciplines: Computer Science, Data Science, Artificial Intelligence, Electrical Engineering,
  Mechanical Engineering, Environmental Science, Public Health, and Agricultural Sciences.
- Minimum CGPA: 3.5 on a 4.0 scale (or equivalent, as assessed by Northgate's Graduate Admissions Office).

AGE REQUIREMENT
Applicants must be no older than 35 years of age at the time of application.

FELLOWSHIP BENEFITS
- Full tuition waiver for the duration of the programme.
- Monthly living stipend of USD 1,200.
- Annual research allowance of USD 1,000.
- Return economy-class airfare upon commencement of studies.
- Health insurance coverage.
- Access to Northgate's research library and digital resources.

REQUIRED DOCUMENTS
1. Completed online application form (available on the fellowship portal).
2. Academic transcripts (certified copies of all university degrees and diplomas).
3. Two academic reference letters (from university professors or academic supervisors).
4. Personal statement (maximum 800 words) describing your research interests and career goals.
5. Valid passport (minimum 18 months validity from the date of application).
6. Proof of English language proficiency: IELTS Academic (minimum 6.5 overall) or TOEFL iBT (minimum 90).
7. Research proposal (for PhD applicants only; maximum 1,500 words).

OTHER ELIGIBILITY CONDITIONS
- Applicants must not hold citizenship of a high-income country (as classified by the World Bank).
- The fellowship may not be held concurrently with any other scholarship or funding award exceeding USD 500 per month.
- Recipients must maintain satisfactory academic progress throughout the award period.
- Applicants must demonstrate financial need through a statement of household income.

APPLICATION DEADLINE
30 April 2025 at 11:59 PM (GMT+0). Late applications will not be considered under any circumstances.

HOW TO APPLY
All applications must be submitted through the Northgate University Fellowship Portal:
https://fellowships.northgate-example.edu/global-excellence

For enquiries, email: fellowships@northgate-example.edu

Northgate University reserves the right to withdraw or modify the fellowship at any time.
This is a fictional sample created for demonstration purposes only.
""".strip()

# ─────────────────────────────────────────────────────────────────────────────
# SESSION STATE
# ─────────────────────────────────────────────────────────────────────────────

def init_session_state():
    defaults = {
        "page": "Home",
        "profile": StudentProfile(),
        "profile_saved": False,
        "opportunity_text": None,
        "opportunity_source": None,
        "extracted_opportunity": None,
        "eligibility_assessment": None,
        "checklist_items": [],
        "model_used": None,
        "analysis_error": None,
        "is_quick_demo": False,
    }
    for key, val in defaults.items():
        if key not in st.session_state:
            st.session_state[key] = val

# ─────────────────────────────────────────────────────────────────────────────
# SIDEBAR
# ─────────────────────────────────────────────────────────────────────────────

def render_sidebar():
    with st.sidebar:
        # ── Logo ──────────────────────────────────────────────────────────────
        st.markdown(
            """
            <div style="padding:1.75rem 1.25rem 0.5rem;">
              <div style="font-size:1.35rem;font-weight:800;color:#fff;letter-spacing:-0.03em;line-height:1;">
                🔍 Opportunity<span style="color:#22c55e;">Lens</span>
              </div>
              <div style="font-size:0.73rem;color:#64748b;margin-top:0.3rem;letter-spacing:0.03em;">
                DISCOVER · ASSESS · APPLY
              </div>
            </div>
            """,
            unsafe_allow_html=True,
        )

        st.markdown('<div style="height:0.75rem;"></div>', unsafe_allow_html=True)
        st.divider()
        st.markdown('<div style="height:0.25rem;"></div>', unsafe_allow_html=True)

        # ── Nav items ─────────────────────────────────────────────────────────
        pages = [
            ("🏠", "Home"),
            ("👤", "My Profile"),
            ("📋", "Analyze Opportunity"),
            ("✅", "Eligibility Results"),
            ("📝", "Application Checklist"),
        ]
        st.markdown('<div style="padding:0 0.75rem;">', unsafe_allow_html=True)
        for icon, name in pages:
            active = st.session_state.page == name
            if st.button(
                f"{icon}  {name}",
                key=f"nav_{name}",
                use_container_width=True,
                type="primary" if active else "secondary",
            ):
                st.session_state.page = name
                st.rerun()
        st.markdown('</div>', unsafe_allow_html=True)

        st.divider()

        # ── Profile card ──────────────────────────────────────────────────────
        p = st.session_state.profile
        if st.session_state.profile_saved and p.full_name:
            initials = "".join(w[0].upper() for w in p.full_name.split()[:2])
            st.markdown(
                f"""
                <div style="margin:0 0.75rem 0.75rem;background:#121f36;border-radius:10px;
                            padding:0.9rem 1rem;border:1px solid #1e3a5f;">
                  <div style="display:flex;align-items:center;gap:0.75rem;margin-bottom:0.6rem;">
                    <div style="width:34px;height:34px;border-radius:50%;background:#16a34a;
                                display:flex;align-items:center;justify-content:center;
                                font-size:0.78rem;font-weight:700;color:white;flex-shrink:0;">
                      {initials}
                    </div>
                    <div>
                      <div style="font-weight:600;color:#e2e8f0;font-size:0.88rem;line-height:1.2;">
                        {p.full_name}
                      </div>
                      <div style="font-size:0.75rem;color:#64748b;">{p.institution or 'No institution'}</div>
                    </div>
                  </div>
                  <div style="display:flex;flex-wrap:wrap;gap:0.35rem;">
                    <span style="background:#1e3a5f;color:#93c5fd;border-radius:4px;
                                 padding:2px 7px;font-size:0.7rem;font-weight:500;">
                      {p.academic_level or '—'}
                    </span>
                    {f'<span style="background:#1e3a5f;color:#86efac;border-radius:4px;padding:2px 7px;font-size:0.7rem;font-weight:500;">CGPA {p.cgpa}/{p.cgpa_scale}</span>' if p.cgpa else ''}
                  </div>
                </div>
                """,
                unsafe_allow_html=True,
            )
        else:
            st.markdown(
                """
                <div style="margin:0 0.75rem 0.75rem;background:#121f36;border-radius:10px;
                            padding:0.9rem 1rem;border:1px dashed #1e3a5f;">
                  <div style="font-size:0.78rem;color:#475569;text-align:center;">
                    No profile set up yet
                  </div>
                </div>
                """,
                unsafe_allow_html=True,
            )

        # ── Last analysis ─────────────────────────────────────────────────────
        if st.session_state.extracted_opportunity:
            opp = st.session_state.extracted_opportunity
            st.markdown(
                f"""
                <div style="margin:0 0.75rem 0.5rem;background:#121f36;border-radius:10px;
                            padding:0.9rem 1rem;border:1px solid #1e3a5f;">
                  <div style="font-size:0.67rem;font-weight:700;letter-spacing:0.06em;
                              text-transform:uppercase;color:#475569;margin-bottom:0.4rem;">
                    Last Analysis
                  </div>
                  <div style="font-size:0.82rem;font-weight:500;color:#cbd5e1;line-height:1.35;">
                    {opp.title or 'Unnamed opportunity'}
                  </div>
                  {f'<div style="font-size:0.7rem;color:#4ade80;margin-top:0.3rem;">via {st.session_state.model_used}</div>' if st.session_state.model_used else ''}
                </div>
                """,
                unsafe_allow_html=True,
            )

# ─────────────────────────────────────────────────────────────────────────────
# PAGE: HOME
# ─────────────────────────────────────────────────────────────────────────────

def page_home():
    p = st.session_state.profile
    has_profile = st.session_state.profile_saved
    has_analysis = st.session_state.extracted_opportunity is not None
    has_results  = st.session_state.eligibility_assessment is not None
    has_list     = bool(st.session_state.checklist_items)

    # ── Hero ──────────────────────────────────────────────────────────────────
    st.markdown(
        f"""
        <div class="ol-hero">
          <div class="ol-hero-logo">Opportunity<span>Lens</span></div>
          <div class="ol-hero-tag">Discover opportunities &middot; Understand your eligibility &middot; Take action</div>
          <div style="display:flex;gap:0.75rem;flex-wrap:wrap;">
            <span style="background:#f0fdf4;border:1px solid #bbf7d0;color:#15803d;
                         border-radius:6px;padding:0.3rem 0.75rem;font-size:0.78rem;font-weight:600;">
              ✦ Powered by Gemma 4
            </span>
            <span style="background:#f0f9ff;border:1px solid #bae6fd;color:#0369a1;
                         border-radius:6px;padding:0.3rem 0.75rem;font-size:0.78rem;font-weight:600;">
              ✦ Transparent Eligibility Engine
            </span>
            <span style="background:#fafafa;border:1px solid {BORDER_MID};color:{SLATE};
                         border-radius:6px;padding:0.3rem 0.75rem;font-size:0.78rem;font-weight:600;">
              ✦ No account required
            </span>
          </div>
        </div>
        """,
        unsafe_allow_html=True,
    )

    # ── Feature strip ─────────────────────────────────────────────────────────
    c1, c2, c3 = st.columns(3)
    features = [
        ("📄", "Upload or Paste", "Submit any scholarship, internship, fellowship, grant or training programme announcement — PDF or plain text."),
        ("🤖", "Gemma 4 Extraction", "Extracts every requirement: eligible countries, CGPA, academic level, documents, deadlines and more."),
        ("🎯", "Clear Assessment", "Per-requirement MET / NOT MET / VERIFY results — rule-based, transparent and fully explained."),
    ]
    for col, (icon, title, body) in zip([c1, c2, c3], features):
        with col:
            st.markdown(
                f"""<div class="ol-feature">
                  <div class="ol-feature-icon">{icon}</div>
                  <div class="ol-feature-title">{title}</div>
                  <div class="ol-feature-body">{body}</div>
                </div>""",
                unsafe_allow_html=True,
            )

    st.markdown("<div style='height:1.5rem;'></div>", unsafe_allow_html=True)

    # ── Two-column layout ─────────────────────────────────────────────────────
    col_steps, col_actions = st.columns([3, 2], gap="large")

    with col_steps:
        st.markdown(
            f'<div style="font-size:1rem;font-weight:700;color:{NAVY};margin-bottom:0.75rem;">Your progress</div>',
            unsafe_allow_html=True,
        )
        steps = [
            ("My Profile",           "Enter your academic details",        has_profile),
            ("Analyze Opportunity",  "Upload or paste an announcement",    has_analysis),
            ("Eligibility Results",  "Review your personalised assessment",has_results),
            ("Application Checklist","Track your preparation tasks",       has_list),
        ]
        for idx, (name, desc, done) in enumerate(steps, 1):
            num_class = "done" if done else "todo"
            num_label = "✓" if done else str(idx)
            st.markdown(
                f"""<div class="ol-step">
                  <div class="ol-step-num {num_class}">{num_label}</div>
                  <div>
                    <div class="ol-step-label">{name}</div>
                    <div class="ol-step-desc">{desc}</div>
                  </div>
                </div>""",
                unsafe_allow_html=True,
            )

    with col_actions:
        st.markdown(
            f'<div style="font-size:1rem;font-weight:700;color:{NAVY};margin-bottom:0.75rem;">Get started</div>',
            unsafe_allow_html=True,
        )
        if st.button("👤  Set up my profile", use_container_width=True,
                     type="secondary" if has_profile else "primary"):
            st.session_state.page = "My Profile"
            st.rerun()

        if st.button("📋  Analyze an opportunity", use_container_width=True,
                     type="primary"):
            st.session_state.page = "Analyze Opportunity"
            st.rerun()

        if has_results:
            if st.button("✅  View eligibility results", use_container_width=True, type="secondary"):
                st.session_state.page = "Eligibility Results"
                st.rerun()

        if has_list:
            if st.button("📝  Open application checklist", use_container_width=True, type="secondary"):
                st.session_state.page = "Application Checklist"
                st.rerun()

# ─────────────────────────────────────────────────────────────────────────────
# PAGE: MY PROFILE
# ─────────────────────────────────────────────────────────────────────────────

def page_profile():
    st.markdown(
        f"""<div class="ol-page-header">
          <div class="ol-page-title">👤 My Academic Profile</div>
          <div class="ol-page-sub">Your details are used for eligibility comparisons.
            Stored only in this browser session — never sent to a server.</div>
        </div>""",
        unsafe_allow_html=True,
    )

    p = st.session_state.profile

    with st.form("profile_form"):
        # ── Personal ──────────────────────────────────────────────────────────
        st.markdown('<div class="ol-section-label">Personal information</div>', unsafe_allow_html=True)
        col1, col2 = st.columns(2)
        with col1:
            full_name = st.text_input("Full Name *", value=p.full_name, placeholder="e.g. Amara Osei")
        with col2:
            country = st.text_input("Country *", value=p.country, placeholder="e.g. Nigeria")

        # ── Academic ──────────────────────────────────────────────────────────
        st.markdown('<div class="ol-section-label">Academic details</div>', unsafe_allow_html=True)
        col3, col4 = st.columns(2)
        with col3:
            institution = st.text_input("Institution", value=p.institution, placeholder="e.g. University of Lagos")
        with col4:
            course = st.text_input("Course of Study", value=p.course_of_study, placeholder="e.g. Computer Science")

        level_options = [
            "Undergraduate (Year 1)", "Undergraduate (Year 2)",
            "Undergraduate (Year 3)", "Undergraduate (Final Year)",
            "Masters", "PhD", "Post-Doctoral", "Other",
        ]
        current_level = p.academic_level if p.academic_level in level_options else "Masters"
        academic_level = st.selectbox("Academic Level *", level_options,
                                      index=level_options.index(current_level))

        # ── CGPA ─────────────────────────────────────────────────────────────
        st.markdown('<div class="ol-section-label">CGPA / GPA</div>', unsafe_allow_html=True)
        col5, col6, col7 = st.columns([2, 2, 2])
        with col5:
            cgpa_str = st.text_input("CGPA", value=str(p.cgpa) if p.cgpa is not None else "",
                                     placeholder="e.g. 3.8")
        with col6:
            scale_options = ["Not specified", "4.0", "5.0", "7.0", "10.0", "100 (percentage)"]
            current_scale = str(p.cgpa_scale) if p.cgpa_scale else "Not specified"
            if current_scale not in scale_options:
                scale_options.append(current_scale)
            cgpa_scale_str = st.selectbox("Grading Scale", scale_options)
        with col7:
            age_str = st.text_input("Age (optional)", value=str(p.age) if p.age is not None else "",
                                    placeholder="e.g. 24")

        # ── Qualifications ────────────────────────────────────────────────────
        st.markdown('<div class="ol-section-label">Qualifications & achievements</div>', unsafe_allow_html=True)
        qualifications = st.text_area(
            "Relevant qualifications, awards, certifications, publications…",
            value=p.qualifications,
            placeholder="Dean's list 2023, IELTS 7.5, published in IEEE conference, Volunteer tutor…",
            height=110,
        )

        st.markdown("<div style='height:0.5rem;'></div>", unsafe_allow_html=True)
        submitted = st.form_submit_button("💾  Save Profile", type="primary", use_container_width=True)

    if submitted:
        errors = []
        cgpa_val, cgpa_scale_val, age_val = None, None, None

        if not full_name.strip():
            errors.append("Full name is required.")

        if cgpa_str.strip():
            try:
                cgpa_val = float(cgpa_str.strip())
                if not 0 <= cgpa_val <= 100:
                    errors.append("CGPA must be a positive number.")
            except ValueError:
                errors.append("CGPA must be a number (e.g. 3.8).")

        if cgpa_scale_str != "Not specified":
            try:
                cgpa_scale_val = float(cgpa_scale_str.split()[0])
            except ValueError:
                errors.append("Could not parse grading scale.")

        if age_str.strip():
            try:
                age_val = int(age_str.strip())
                if not 15 <= age_val <= 80:
                    errors.append("Please enter a realistic age (15–80).")
            except ValueError:
                errors.append("Age must be a whole number.")

        if errors:
            for err in errors:
                st.error(err)
        else:
            st.session_state.profile = StudentProfile(
                full_name=full_name.strip(),
                country=country.strip(),
                institution=institution.strip(),
                course_of_study=course.strip(),
                academic_level=academic_level,
                cgpa=cgpa_val,
                cgpa_scale=cgpa_scale_val,
                qualifications=qualifications.strip(),
                age=age_val,
            )
            st.session_state.profile_saved = True
            st.success("✅ Profile saved! You can now analyze an opportunity.")

# ─────────────────────────────────────────────────────────────────────────────
# PAGE: ANALYZE OPPORTUNITY
# ─────────────────────────────────────────────────────────────────────────────

def page_analyze():
    st.markdown(
        f"""<div class="ol-page-header">
          <div class="ol-page-title">📋 Analyze an Opportunity</div>
          <div class="ol-page-sub">Upload a PDF, paste text, or load the built-in sample to run a full Gemma 4 analysis.</div>
        </div>""",
        unsafe_allow_html=True,
    )

    # ── Profile nudge ─────────────────────────────────────────────────────────
    if not st.session_state.profile_saved:
        st.warning("⚠️ Complete your profile first to receive a personalized eligibility assessment.", icon="👤")
        if st.button("→ Set up My Profile", type="primary"):
            st.session_state.page = "My Profile"
            st.rerun()
        st.markdown('<div class="ol-divider"></div>', unsafe_allow_html=True)

    # ── MODE 1: QUICK DEMO (Instant — No API Call) ───────────────────────────
    render_html(
        f"""<div style="background:{SURFACE};border:1.5px solid #bbf7d0;border-radius:12px;padding:1.4rem 1.6rem;margin-bottom:1.5rem;box-shadow:0 1px 3px rgba(0,0,0,0.04);">
          <div style="display:flex;align-items:center;gap:0.5rem;margin-bottom:0.5rem;">
            <span class="ol-demo-pill" style="background:#f0fdf4;border-color:#bbf7d0;color:{GREEN_TEXT};">⚡ Mode 1: Quick Demo</span>
            <span style="font-size:0.72rem;font-weight:700;color:{GREEN_TEXT};background:#dcfce7;border-radius:4px;padding:2px 7px;">INSTANT · NO API CALL</span>
          </div>
          <div style="font-size:1.05rem;font-weight:700;color:{NAVY};margin-bottom:0.25rem;">
            Explore OpportunityLens in seconds
          </div>
          <div style="font-size:0.85rem;color:{SLATE};margin-bottom:0.85rem;line-height:1.5;">
            Uses verified precomputed requirements from the fictional Northgate Excellence Fellowship. Tests the transparent rule-based eligibility engine and interactive preparation checklist with zero latency.
          </div>
        </div>"""
    )
    if st.button("⚡  Launch Instant Quick Demo (0s)", type="primary", key="btn_quick_demo"):
        _run_quick_demo()

    render_html('<div class="ol-divider"></div>')

    # ── MODE 2: LIVE AI ANALYSIS (Gemma 4 Powered) ────────────────────────────
    render_html(
        f"""<div style="background:{SURFACE};border:1px solid {BORDER};border-radius:12px;padding:1.4rem 1.6rem;margin-bottom:1.25rem;box-shadow:0 1px 3px rgba(0,0,0,0.04);">
          <div style="display:flex;align-items:center;gap:0.5rem;margin-bottom:0.5rem;">
            <span class="ol-demo-pill" style="background:#eff6ff;border-color:#bfdbfe;color:#1d4ed8;">🤖 Mode 2: Live AI Analysis</span>
            <span style="font-size:0.72rem;font-weight:700;color:#1d4ed8;background:#dbeafe;border-radius:4px;padding:2px 7px;">GEMMA 4 · LIVE EXTRACTION</span>
          </div>
          <div style="font-size:1.05rem;font-weight:700;color:{NAVY};margin-bottom:0.25rem;">
            Real-Time Analysis via Google Gen AI SDK
          </div>
          <div style="font-size:0.85rem;color:{SLATE};line-height:1.5;">
            Submits the announcement directly to Google's <code>gemma-4-26b-a4b-it</code> model to extract requirements and conditions dynamically.
          </div>
        </div>"""
    )

    tab_sample, tab_pdf, tab_text = st.tabs([
        "🎓  Sample Announcement (Live)",
        "📎  Upload PDF",
        "📝  Paste Text",
    ])

    with tab_sample:
        st.markdown("<div style='height:0.5rem;'></div>", unsafe_allow_html=True)
        st.markdown(
            "Run live Gemma 4 extraction on the full text of the Northgate University Fellowship announcement. "
            "This sends the announcement to the Gemma 4 API and extracts all structured requirements in real time."
        )
        if st.button("🤖  Run Live Gemma 4 Analysis on Sample Announcement", type="primary", key="live_sample"):
            _run_analysis(SAMPLE_OPPORTUNITY_TEXT, source="Live AI Sample: Northgate Fellowship")

    with tab_pdf:
        st.markdown("<div style='height:0.5rem;'></div>", unsafe_allow_html=True)
        st.markdown(
            """<div class="ol-upload-zone">
              <div style="font-size:1.8rem;margin-bottom:0.5rem;">📎</div>
              <div style="font-size:0.9rem;font-weight:600;color:#0f172a;margin-bottom:0.25rem;">
                Drop your PDF announcement here
              </div>
              <div style="font-size:0.8rem;color:#64748b;">Max 20 MB · Password-protected PDFs not supported</div>
            </div>""",
            unsafe_allow_html=True,
        )
        uploaded = st.file_uploader(
            "Upload PDF",
            type=["pdf"],
            label_visibility="collapsed",
        )
        if uploaded is not None:
            sz_kb = len(uploaded.getvalue()) / 1024
            st.markdown(
                f"""<div style="background:#f8fafc;border:1px solid #e2e8f0;border-radius:8px;
                               padding:0.6rem 1rem;font-size:0.85rem;color:#0f172a;margin:0.5rem 0;
                               display:flex;align-items:center;gap:0.5rem;">
                  <span>📄</span>
                  <span><strong>{uploaded.name}</strong> &mdash; {sz_kb:.1f} KB</span>
                </div>""",
                unsafe_allow_html=True,
            )
            if st.button("🔍  Analyze PDF", type="primary", key="analyze_pdf"):
                result = extract_text_from_pdf(uploaded.getvalue(), uploaded.name)
                if not result.success:
                    st.error(f"❌ {result.error}")
                else:
                    if result.warning:
                        st.warning(f"⚠️ {result.warning}")
                    st.success(f"✅ Extracted {result.char_count:,} characters from {result.page_count} page(s).")
                    _run_analysis(result.text, source=f"PDF: {uploaded.name}")

    with tab_text:
        st.markdown("<div style='height:0.5rem;'></div>", unsafe_allow_html=True)
        pasted = st.text_area(
            "Paste the full announcement text:",
            height=280,
            placeholder="Paste the complete text of the scholarship, internship, fellowship, grant, or training programme announcement…",
            label_visibility="visible",
        )
        if st.button("🔍  Analyze Text", type="primary", key="analyze_text"):
            result = validate_pasted_text(pasted)
            if not result.success:
                st.error(f"❌ {result.error}")
            else:
                if result.warning:
                    st.warning(f"⚠️ {result.warning}")
                _run_analysis(result.text, source="pasted text")


def _run_quick_demo():
    """Load precomputed sample opportunity and calculate eligibility instantly without LLM API call."""
    st.session_state.analysis_error = None
    if not st.session_state.profile_saved or not st.session_state.profile.full_name:
        st.session_state.profile = StudentProfile(
            full_name="Amara Osei (Demo Student)",
            country="Nigeria",
            institution="University of Lagos",
            course_of_study="Computer Science",
            academic_level="Masters",
            cgpa=3.8,
            cgpa_scale=4.0,
            qualifications="B.Sc. Computer Science (First Class Honours), IELTS Academic 7.5, 2 published workshop papers",
            age=24,
        )
        st.session_state.profile_saved = True

    sample_opp = gemma_service.get_sample_extracted_opportunity()
    st.session_state.extracted_opportunity = sample_opp
    st.session_state.opportunity_text = SAMPLE_OPPORTUNITY_TEXT
    st.session_state.opportunity_source = "Precomputed Sample Demo"
    st.session_state.model_used = "Precomputed Demo (No API Call)"
    st.session_state.is_quick_demo = True

    assessment = run_eligibility_check(st.session_state.profile, sample_opp)
    st.session_state.eligibility_assessment = assessment
    st.session_state.checklist_items = _build_checklist(sample_opp, assessment)
    st.session_state.page = "Eligibility Results"
    st.rerun()


def _run_analysis(text: str, source: str):
    """Run Gemma 4 analysis and eligibility check — identical logic to original."""
    st.session_state.analysis_error = None
    st.session_state.is_quick_demo = False

    api_key = gemma_service.get_api_key()
    if not api_key:
        st.error(
            "❌ **API key not configured.** Add `GEMINI_API_KEY=your-key` to a `.env` file "
            "or to `.streamlit/secrets.toml` for Streamlit Community Cloud."
        )
        return

    with st.spinner("🤖 Gemma 4 is analyzing the announcement… this usually takes 15–30 seconds."):
        try:
            opportunity, model_used = gemma_service.extract_opportunity(text)
            st.session_state.extracted_opportunity = opportunity
            st.session_state.opportunity_text = text
            st.session_state.opportunity_source = source
            st.session_state.model_used = model_used
        except ValueError as exc:
            st.error(f"❌ Configuration error: {exc}")
            return
        except RuntimeError as exc:
            st.error(f"❌ Analysis failed: {exc}")
            return
        except Exception as exc:
            st.error(f"❌ Unexpected error: {exc}")
            return

    if st.session_state.profile_saved:
        assessment = run_eligibility_check(st.session_state.profile, opportunity)
        st.session_state.eligibility_assessment = assessment
        st.session_state.checklist_items = _build_checklist(opportunity, assessment)
    else:
        st.session_state.eligibility_assessment = None
        st.session_state.checklist_items = []

    st.success(f"✅ Analysis complete using **{model_used}**.")
    if st.button("→ View Eligibility Results", type="primary"):
        st.session_state.page = "Eligibility Results"
        st.rerun()


def _build_checklist(opp: ExtractedOpportunity, assessment: EligibilityAssessment) -> list:
    items = []
    for doc in opp.required_documents:
        items.append(ChecklistItem(id=str(uuid.uuid4()), category="document",
                                   description=f"Obtain: {doc.name}", detail=doc.description))
    for check in assessment.requirement_checks:
        if check.status == "NEEDS_VERIFICATION":
            items.append(ChecklistItem(id=str(uuid.uuid4()), category="verification",
                                       description=f"Verify: {check.requirement}", detail=check.explanation))
    standard_actions = [
        ("Review full announcement for any conditions not captured above", None),
        ("Contact the awarding institution if you have eligibility questions", None),
        ("Prepare a compelling personal statement", "Tailored to this specific opportunity"),
        ("Submit application before the deadline", opp.application_deadline or "Deadline not specified"),
    ]
    if opp.official_url:
        standard_actions.insert(0, (f"Apply online at: {opp.official_url}", None))
    for desc, detail in standard_actions:
        items.append(ChecklistItem(id=str(uuid.uuid4()), category="action",
                                   description=desc, detail=detail))
    return items

# ─────────────────────────────────────────────────────────────────────────────
# PAGE: ELIGIBILITY RESULTS
# ─────────────────────────────────────────────────────────────────────────────

def render_requirement_card(check: RequirementStatus):
    """Render a single requirement card safely without leaking raw HTML or markdown code blocks."""
    badge_cfg = {
        "MET":                ("ol-badge-met",    "ol-req-card-met",    "✓ Met"),
        "NOT_MET":            ("ol-badge-notmet", "ol-req-card-notmet", "✗ Not Met"),
        "NEEDS_VERIFICATION": ("ol-badge-verify", "ol-req-card-verify", "⚠ Verify"),
        "NOT_SPECIFIED":      ("ol-badge-na",     "ol-req-card-na",     "— N/A"),
    }
    badge_cls, card_cls, badge_label = badge_cfg.get(
        check.status, ("ol-badge-na", "ol-req-card-na", check.status.replace("_", " "))
    )

    req_name = html.escape(check.requirement or "Requirement")
    req_expl = html.escape(check.explanation or "")

    vals_parts = []
    if check.student_value:
        vals_parts.append(f"<strong>Your value:</strong> <code>{html.escape(str(check.student_value))}</code>")
    if check.required_value:
        vals_parts.append(f"<strong>Required:</strong> <code>{html.escape(str(check.required_value))}</code>")

    vals_html = f'<div class="ol-req-vals">{"&nbsp;&nbsp;".join(vals_parts)}</div>' if vals_parts else ""

    excerpt_html = (
        f'<div class="ol-excerpt">📝 From announcement: "{html.escape(str(check.source_excerpt))}"</div>'
        if check.source_excerpt else ""
    )

    card_html = (
        f'<div class="ol-req-card {card_cls}">'
        f'<div style="flex-shrink:0;padding-top:2px;"><span class="ol-badge {badge_cls}">{badge_label}</span></div>'
        f'<div style="flex:1;min-width:0;">'
        f'<div class="ol-req-name">{req_name}</div>'
        f'<div class="ol-req-expl">{req_expl}</div>'
        f'{vals_html}'
        f'{excerpt_html}'
        f'</div>'
        f'</div>'
    )
    render_html(card_html)


def _render_assessment(assessment: EligibilityAssessment):
    # ── Banner ────────────────────────────────────────────────────────────────
    cfg = {
        "LIKELY_ELIGIBLE":      ("ol-assess-eligible",     "✅", "Likely Eligible",          GREEN_TEXT),
        "POTENTIALLY_ELIGIBLE": ("ol-assess-potential",    "⚠️", "Potentially Eligible",     AMBER_TEXT),
        "LIKELY_INELIGIBLE":    ("ol-assess-ineligible",   "❌", "Likely Ineligible",         RED_TEXT),
        "INSUFFICIENT_INFORMATION": ("ol-assess-insufficient","❓","Insufficient Information", SLATE),
    }
    css, icon, label, color = cfg.get(
        assessment.overall_status,
        ("ol-assess-insufficient", "❓", "Unknown", SLATE),
    )
    render_html(
        f"""<div class="ol-assess-banner {css}">
          <div class="ol-assess-icon">{icon}</div>
          <div>
            <div class="ol-assess-status" style="color:{color};">{label}</div>
            <div class="ol-assess-body" style="color:{NAVY};">{html.escape(assessment.overall_explanation)}</div>
          </div>
        </div>"""
    )

    # ── Stat pills ────────────────────────────────────────────────────────────
    m1, m2, m3, m4 = st.columns(4)
    for col, count, label, color in [
        (m1, assessment.met_count,                "Met",           GREEN),
        (m2, assessment.not_met_count,            "Not Met",       RED),
        (m3, assessment.needs_verification_count, "Verify",        AMBER),
        (m4, assessment.not_specified_count,       "Not Specified", SLATE_LT),
    ]:
        with col:
            render_html(
                f"""<div class="ol-stat">
                  <div class="ol-stat-num" style="color:{color};">{count}</div>
                  <div class="ol-stat-label">{label}</div>
                </div>"""
            )

    st.markdown("<div style='height:1.25rem;'></div>", unsafe_allow_html=True)

    # ── Per-requirement cards ─────────────────────────────────────────────────
    render_html(f'<div class="ol-section-label">Requirement breakdown</div>')

    status_order = ["NOT_MET", "NEEDS_VERIFICATION", "MET", "NOT_SPECIFIED"]
    sorted_checks = sorted(
        assessment.requirement_checks,
        key=lambda c: status_order.index(c.status) if c.status in status_order else 99,
    )

    for check in sorted_checks:
        render_requirement_card(check)

    # ── Disclaimer ────────────────────────────────────────────────────────────
    render_html(f'<div class="ol-disclaimer">⚠️ {html.escape(assessment.disclaimer)}</div>')


def page_results():
    st.markdown(
        f"""<div class="ol-page-header">
          <div class="ol-page-title">✅ Eligibility Results</div>
          <div class="ol-page-sub">Powered by structured requirement extraction + a transparent rule-based assessment engine.</div>
        </div>""",
        unsafe_allow_html=True,
    )

    opp: Optional[ExtractedOpportunity] = st.session_state.extracted_opportunity
    assessment: Optional[EligibilityAssessment] = st.session_state.eligibility_assessment

    if opp is None:
        render_html(
            """<div class="ol-empty">
              <div class="ol-empty-icon">📋</div>
              <div class="ol-empty-title">No analysis yet</div>
              <div class="ol-empty-body">Analyze an opportunity to see your eligibility results here.</div>
            </div>"""
        )
        if st.button("← Analyze an Opportunity", type="primary"):
            st.session_state.page = "Analyze Opportunity"
            st.rerun()
        return

    # ── Quick Demo Mode vs Live AI Mode Notice ────────────────────────────────
    if st.session_state.get("is_quick_demo", False):
        render_html(
            f"""<div style="background:#eff6ff;border:1px solid #bfdbfe;border-radius:10px;padding:0.85rem 1.1rem;margin-bottom:1.25rem;display:flex;align-items:flex-start;gap:0.75rem;">
              <span style="font-size:1.3rem;line-height:1;">⚡</span>
              <div>
                <div style="font-weight:700;color:#1e40af;font-size:0.88rem;letter-spacing:0.02em;">QUICK DEMO MODE (PRECOMPUTED SAMPLE DATA)</div>
                <div style="color:#2563eb;font-size:0.82rem;margin-top:0.15rem;line-height:1.45;">
                  These results are illustrative and generated from precomputed sample data without an LLM call. To test fresh AI extraction on this or another announcement, choose <strong>Mode 2: Live AI Analysis</strong> on the Analyze Opportunity page.
                </div>
              </div>
            </div>"""
        )
    else:
        model_name = st.session_state.model_used or "gemma-4-26b-a4b-it"
        render_html(
            f"""<div style="background:#f0fdf4;border:1px solid #bbf7d0;border-radius:10px;padding:0.85rem 1.1rem;margin-bottom:1.25rem;display:flex;align-items:flex-start;gap:0.75rem;">
              <span style="font-size:1.3rem;line-height:1;">🤖</span>
              <div>
                <div style="font-weight:700;color:{GREEN_TEXT};font-size:0.88rem;letter-spacing:0.02em;">LIVE GEMMA 4 ANALYSIS</div>
                <div style="color:{GREEN};font-size:0.82rem;margin-top:0.15rem;line-height:1.45;">
                  Requirements were extracted live from the submitted announcement using Google's <code>{html.escape(model_name)}</code> model via Google Gen AI SDK.
                </div>
              </div>
            </div>"""
        )

    # ── Opportunity overview card ──────────────────────────────────────────────
    model_used = st.session_state.model_used or "gemma-4-26b-a4b-it"
    cat_pill = f'<span class="ol-opp-pill">{(opp.category or "opportunity").title()}</span>' if opp.category else ""
    url_html = (f'<a href="{opp.official_url}" target="_blank" '
                f'style="color:#16a34a;font-weight:600;font-size:0.88rem;">'
                f'🔗 Apply here ↗</a>') if opp.official_url else "—"

    desc_html = f'<div style="font-size:0.88rem;color:#475569;margin-top:0.75rem;line-height:1.55;">{html.escape(opp.description)}</div>' if opp.description else ""
    benefits_html = ""
    if opp.benefits:
        b_items = "".join(f'<div style="font-size:0.85rem;color:#475569;padding:0.15rem 0;">• {html.escape(b)}</div>' for b in opp.benefits)
        benefits_html = f'<div style="margin-top:0.75rem;padding-top:0.75rem;border-top:1px solid #e2e8f0;"><div style="font-size:0.78rem;font-weight:700;color:#64748b;text-transform:uppercase;letter-spacing:0.05em;margin-bottom:0.4rem;">Benefits</div>{b_items}</div>'
    notes_html = f'<div style="margin-top:0.75rem;background:#fffbeb;border:1px solid #fde68a;border-radius:6px;padding:0.5rem 0.75rem;font-size:0.8rem;color:#92400e;">ℹ️ {html.escape(opp.extraction_notes)}</div>' if opp.extraction_notes else ""

    opp_html = (
        f'<div class="ol-opp-card">'
        f'<div style="display:flex;align-items:flex-start;justify-content:space-between;flex-wrap:gap:0.5rem;">'
        f'<div>'
        f'<div class="ol-opp-title">{html.escape(opp.title or "Untitled opportunity")}</div>'
        f'<div class="ol-opp-org">{html.escape(opp.organizing_institution or "")}</div>'
        f'{cat_pill}'
        f'</div>'
        f'</div>'
        f'{desc_html}'
        f'<div class="ol-opp-meta-row">'
        f'<div class="ol-opp-meta-item"><span class="ol-opp-meta-key">⏰ Deadline</span><span class="ol-opp-meta-val">{html.escape(opp.application_deadline or "Not specified")}</span></div>'
        f'<div class="ol-opp-meta-item"><span class="ol-opp-meta-key">🔗 Application</span><span class="ol-opp-meta-val">{url_html}</span></div>'
        f'<div class="ol-opp-meta-item"><span class="ol-opp-meta-key">🤖 Mode / Model</span><span class="ol-opp-meta-val" style="font-family:monospace;font-size:0.82rem;">{html.escape(model_used)}</span></div>'
        f'</div>'
        f'{benefits_html}'
        f'{notes_html}'
        f'</div>'
    )
    render_html(opp_html)

    # ── Assessment ────────────────────────────────────────────────────────────
    if not st.session_state.profile_saved:
        st.warning("⚠️ No profile found. Add your academic details for a personalized assessment.")
        if st.button("→ Set up My Profile", type="primary"):
            st.session_state.page = "My Profile"
            st.rerun()
    elif assessment:
        _render_assessment(assessment)

    # ── Extracted requirements tabs ───────────────────────────────────────────
    render_html(f'<div class="ol-section-label">Extracted requirements</div>')

    req_tabs = st.tabs(["🌍 Countries", "🎓 Level & Course", "📊 CGPA", "📄 Documents", "⚙️ Other"])

    with req_tabs[0]:
        ec = opp.eligible_countries
        if ec.is_open_to_all:
            st.success("🌍 Open to applicants from all countries.")
        elif ec.countries:
            student_country = st.session_state.profile.country.lower() if st.session_state.profile_saved else ""
            for c in ec.countries:
                matched = bool(student_country and student_country in c.lower())
                dot = "✅" if matched else "•"
                style = f"color:{GREEN_TEXT};font-weight:600;" if matched else f"color:{SLATE};"
                render_html(f'<div style="{style}padding:0.15rem 0;font-size:0.88rem;">{dot} {html.escape(c)}</div>')
        else:
            st.info("No country restriction specified in the announcement.")
        if ec.raw_text:
            render_html(f'<div class="ol-excerpt">📝 "{html.escape(ec.raw_text)}"</div>')

    with req_tabs[1]:
        if opp.academic_level_requirements:
            render_html(f'<div style="font-size:0.78rem;font-weight:700;color:{SLATE};letter-spacing:0.05em;text-transform:uppercase;margin-bottom:0.4rem;">Academic Level</div>')
            for lvl in opp.academic_level_requirements:
                render_html(f'<div style="font-size:0.88rem;color:{SLATE};padding:0.15rem 0;">• {html.escape(lvl)}</div>')
        else:
            st.info("No academic level requirement specified.")
        if opp.course_restrictions:
            render_html(f'<div style="font-size:0.78rem;font-weight:700;color:{SLATE};letter-spacing:0.05em;text-transform:uppercase;margin:0.75rem 0 0.4rem;">Eligible Disciplines</div>')
            for c in opp.course_restrictions:
                render_html(f'<div style="font-size:0.88rem;color:{SLATE};padding:0.15rem 0;">• {html.escape(c)}</div>')

    with req_tabs[2]:
        cgpa_req = opp.cgpa_requirement
        if cgpa_req.minimum is not None:
            scale_str = f" / {cgpa_req.scale}" if cgpa_req.scale else ""
            render_html(
                f"""<div style="background:#f0fdf4;border:1px solid #bbf7d0;border-radius:8px;padding:1rem 1.25rem;display:inline-block;margin-bottom:0.5rem;">
                  <div style="font-size:0.72rem;font-weight:700;letter-spacing:0.06em;text-transform:uppercase;color:{GREEN_TEXT};margin-bottom:0.2rem;">Minimum CGPA</div>
                  <div style="font-size:1.6rem;font-weight:800;color:{GREEN_TEXT};line-height:1;">
                    {cgpa_req.minimum}{scale_str}
                  </div>
                </div>"""
            )
            if cgpa_req.raw_text:
                render_html(f'<div class="ol-excerpt">📝 "{html.escape(cgpa_req.raw_text)}"</div>')
        else:
            st.info("No CGPA requirement specified.")

    with req_tabs[3]:
        if opp.required_documents:
            for doc in opp.required_documents:
                badge_color = RED_TEXT if doc.is_mandatory else "#1d4ed8"
                badge_bg    = "#fee2e2" if doc.is_mandatory else "#eff6ff"
                badge_label = "Mandatory" if doc.is_mandatory else "Optional"
                desc_html = f'<div style="font-size:0.8rem;color:{SLATE};margin-top:0.1rem;">{html.escape(doc.description)}</div>' if doc.description else ''
                render_html(
                    f"""<div style="display:flex;align-items:flex-start;gap:0.75rem;padding:0.6rem 0;border-bottom:1px solid {BORDER};">
                      <span style="background:{badge_bg};color:{badge_color};border-radius:4px;padding:2px 8px;font-size:0.7rem;font-weight:700;flex-shrink:0;margin-top:1px;">{badge_label}</span>
                      <div>
                        <div style="font-size:0.88rem;font-weight:600;color:{NAVY};">{html.escape(doc.name)}</div>
                        {desc_html}
                      </div>
                    </div>"""
                )
        else:
            st.info("No required documents listed.")

    with req_tabs[4]:
        age_req = opp.age_requirement
        if age_req.minimum_age or age_req.maximum_age:
            parts = []
            if age_req.minimum_age:
                parts.append(f"Minimum age: {age_req.minimum_age}")
            if age_req.maximum_age:
                parts.append(f"Maximum age: {age_req.maximum_age}")
            render_html(
                f'<div style="font-size:0.88rem;font-weight:600;color:{NAVY};padding:0.4rem 0;">'
                + " &nbsp;·&nbsp; ".join(parts) + "</div>"
            )
            if age_req.raw_text:
                render_html(f'<div class="ol-excerpt">📝 "{html.escape(age_req.raw_text)}"</div>')
        if opp.other_eligibility_conditions:
            render_html(f'<div style="font-size:0.78rem;font-weight:700;color:{SLATE};letter-spacing:0.05em;text-transform:uppercase;margin:0.75rem 0 0.4rem;">Other conditions</div>')
            for cond in opp.other_eligibility_conditions:
                render_html(f'<div style="font-size:0.85rem;color:{SLATE};padding:0.2rem 0;border-bottom:1px solid {BORDER};">• {html.escape(cond)}</div>')
        if not (age_req.minimum_age or age_req.maximum_age) and not opp.other_eligibility_conditions:
            st.info("No additional conditions specified.")


# ─────────────────────────────────────────────────────────────────────────────
# PAGE: APPLICATION CHECKLIST
# ─────────────────────────────────────────────────────────────────────────────

def page_checklist():
    st.markdown(
        f"""<div class="ol-page-header">
          <div class="ol-page-title">📝 Application Checklist</div>
          <div class="ol-page-sub">Track every step of your application preparation.</div>
        </div>""",
        unsafe_allow_html=True,
    )

    opp: Optional[ExtractedOpportunity] = st.session_state.extracted_opportunity
    items: list = st.session_state.checklist_items

    if opp is None:
        render_html(
            """<div class="ol-empty">
              <div class="ol-empty-icon">📝</div>
              <div class="ol-empty-title">No checklist yet</div>
              <div class="ol-empty-body">Analyze an opportunity to generate your personalized application checklist.</div>
            </div>"""
        )
        if st.button("← Analyze an Opportunity", type="primary"):
            st.session_state.page = "Analyze Opportunity"
            st.rerun()
        return

    if not items:
        st.info("No checklist items were generated — the announcement may have had very few stated requirements.")
        return

    # ── Progress header ───────────────────────────────────────────────────────
    completed = sum(1 for i in items if i.completed)
    total = len(items)
    pct = int(completed / total * 100) if total else 0

    deadline_html = f"&nbsp;·&nbsp; ⏰ <strong>Deadline:</strong> {html.escape(opp.application_deadline)}" if opp.application_deadline else ""
    url_html = (f'&nbsp;·&nbsp; <a href="{opp.official_url}" target="_blank" '
                f'style="color:{GREEN};font-weight:600;font-size:0.82rem;">🔗 Apply ↗</a>') if opp.official_url else ""

    render_html(
        f"""<div class="ol-cl-header">
          <div style="display:flex;align-items:flex-start;justify-content:space-between;flex-wrap:wrap;gap:0.5rem;">
            <div>
              <div class="ol-cl-title">{html.escape(opp.title or 'Application Checklist')}</div>
              <div class="ol-cl-meta" style="color:{SLATE};font-size:0.82rem;">
                {html.escape(opp.organizing_institution or '')}
                {deadline_html}
                {url_html}
              </div>
            </div>
            <div style="text-align:right;flex-shrink:0;">
              <div style="font-size:1.6rem;font-weight:800;color:{GREEN if pct==100 else NAVY};line-height:1;">
                {pct}%
              </div>
              <div style="font-size:0.72rem;font-weight:600;letter-spacing:0.05em;text-transform:uppercase;color:{SLATE_LT};">
                {completed} of {total} done
              </div>
            </div>
          </div>
          <div class="ol-cl-progress-bar" style="margin-top:0.75rem;">
            <div class="ol-cl-progress-fill" style="width:{pct}%;"></div>
          </div>
        </div>"""
    )

    # ── Group by category ─────────────────────────────────────────────────────
    cat_config = {
        "document":     ("📄 Required Documents",         "chip-doc",    "document"),
        "verification": ("🔍 Items Needing Verification",  "chip-verify", "verify"),
        "action":       ("📌 Application Actions",         "chip-action", "action"),
    }

    grouped: dict[str, list] = {"document": [], "verification": [], "action": []}
    for item in items:
        cat = item.category if item.category in grouped else "action"
        grouped[cat].append(item)

    for cat_key, (section_title, chip_cls, chip_label) in cat_config.items():
        cat_items = grouped[cat_key]
        if not cat_items:
            continue

        done_in_cat = sum(1 for i in cat_items if i.completed)
        render_html(
            f"""<div class="ol-cl-section">
              {section_title}
              <span style="font-weight:400;font-size:0.7rem;color:{SLATE_LT};margin-left:0.4rem;">
                ({done_in_cat}/{len(cat_items)})
              </span>
            </div>"""
        )

        for item in cat_items:
            main_idx = next((i for i, it in enumerate(items) if it.id == item.id), None)
            col_cb, col_body = st.columns([0.04, 0.96])
            with col_cb:
                checked = st.checkbox(
                    "", value=item.completed, key=f"check_{item.id}", label_visibility="collapsed"
                )
            with col_body:
                done_cls = "done" if checked else ""
                desc_txt = html.escape(item.description)
                detail_html = (
                    f'<div class="ol-cl-item-detail">{html.escape(item.detail)}</div>'
                    if item.detail else ""
                )
                item_html = (
                    f'<div class="ol-cl-item {done_cls}" style="margin-top:-0.1rem;">'
                    f'<div style="flex:1;">'
                    f'<div class="ol-cl-item-text {done_cls}">{desc_txt}</div>'
                    f'{detail_html}'
                    f'</div>'
                    f'</div>'
                )
                render_html(item_html)

            if main_idx is not None and checked != items[main_idx].completed:
                items[main_idx].completed = checked
                st.session_state.checklist_items = items
                st.rerun()

    st.markdown("<div style='height:1rem;'></div>", unsafe_allow_html=True)

    col_r, _ = st.columns([1, 3])
    with col_r:
        if st.button("↺  Reset all items", use_container_width=True):
            for item in items:
                item.completed = False
            st.session_state.checklist_items = items
            st.rerun()

# ─────────────────────────────────────────────────────────────────────────────
# MAIN
# ─────────────────────────────────────────────────────────────────────────────

def main():
    st.markdown(CUSTOM_CSS, unsafe_allow_html=True)
    init_session_state()
    render_sidebar()

    page = st.session_state.page
    if page == "Home":
        page_home()
    elif page == "My Profile":
        page_profile()
    elif page == "Analyze Opportunity":
        page_analyze()
    elif page == "Eligibility Results":
        page_results()
    elif page == "Application Checklist":
        page_checklist()
    else:
        page_home()


if __name__ == "__main__":
    main()
