"""
src/ui/styles.py — 글로벌 CSS 스타일
앱 전체에 적용되는 다크 테마 CSS를 관리합니다.
"""
import streamlit as st

_GLOBAL_CSS = """
<style>
/* ── 전체 배경 ─────────────────────────────────── */
[data-testid="stAppViewContainer"] {
    background: linear-gradient(135deg, #0d1117 0%, #0f1923 50%, #111827 100%);
    min-height: 100vh;
}
[data-testid="stHeader"] { background: transparent; }

/* ── 사이드바 ──────────────────────────────────── */
[data-testid="stSidebar"] {
    background: linear-gradient(180deg, #0d1f2d 0%, #0a1628 100%);
    border-right: 1px solid rgba(255,255,255,0.07);
}

/* ── 탭 ────────────────────────────────────────── */
.stTabs [data-baseweb="tab-list"] {
    gap: 8px;
    background: rgba(255,255,255,0.03);
    padding: 6px;
    border-radius: 12px;
}
.stTabs [data-baseweb="tab"] {
    border-radius: 8px;
    padding: 8px 20px;
    color: rgba(255,255,255,0.5);
    font-weight: 500;
    transition: all 0.2s;
}
.stTabs [aria-selected="true"] {
    background: linear-gradient(135deg, #1a6b4a, #0d3d6e) !important;
    color: white !important;
}

/* ── 메트릭 카드 ───────────────────────────────── */
[data-testid="metric-container"] {
    background: rgba(255,255,255,0.04);
    border: 1px solid rgba(255,255,255,0.08);
    border-radius: 12px;
    padding: 16px;
}

/* ── 버튼 ──────────────────────────────────────── */
.stButton > button {
    background: linear-gradient(135deg, #00C896, #0070f3);
    color: white;
    border: none;
    border-radius: 10px;
    font-weight: 600;
    transition: all 0.25s;
    box-shadow: 0 4px 15px rgba(0,200,150,0.2);
}
.stButton > button:hover {
    transform: translateY(-2px);
    box-shadow: 0 6px 20px rgba(0,200,150,0.35);
}

/* ── 폼 ────────────────────────────────────────── */
[data-testid="stForm"] {
    background: rgba(255,255,255,0.03);
    border: 1px solid rgba(255,255,255,0.07);
    border-radius: 16px;
    padding: 20px;
}

/* ── 기타 ──────────────────────────────────────── */
.stDataFrame { border-radius: 10px; overflow: hidden; }
.stAlert     { border-radius: 10px; }
hr           { border-color: rgba(255,255,255,0.07) !important; }
h2           { color: #e2e8f0 !important; }
h3, h4       { color: #cbd5e1 !important; }
</style>
"""


def inject_global_css() -> None:
    """앱 전체 CSS를 주입합니다. app.py에서 최초 1회 호출하세요."""
    st.markdown(_GLOBAL_CSS, unsafe_allow_html=True)
