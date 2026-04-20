import streamlit as st

from src.ui.cashflow_tab import render_cashflow_tab
from src.ui.recommend_tab import render_recommend_tab
from src.ui.risk_tab import render_risk_tab
from src.ui.sidebar import render_sidebar
from src.ui.styles import inject_global_css

# Page Configuration
st.set_page_config(
    page_title="smecheck.cloud - 흑자도산 방지 대시보드",
    page_icon="🛡️",
    layout="wide",
    initial_sidebar_state="expanded",
)

# Initialize UI
inject_global_css()
render_sidebar()

# Main Header
st.markdown("""
<div style="
    background: linear-gradient(135deg, rgba(0,200,150,0.08), rgba(0,112,243,0.08));
    border: 1px solid rgba(0,200,150,0.15);
    border-radius: 16px;
    padding: 24px 32px;
    margin-bottom: 24px;
">
    <h1 style="
        margin: 0;
        font-size: 1.9rem;
        font-weight: 800;
        background: linear-gradient(90deg, #00C896, #4B9EFF);
        -webkit-background-clip: text;
        -webkit-text-fill-color: transparent;
    ">🛡️ 소상공인 흑자도산 방지 대시보드</h1>
    <p style="margin: 8px 0 0 0; color: rgba(255,255,255,0.55); font-size: 0.95rem;">
        현금흐름 예측 · 위험도 진단 · 정책자금 추천
    </p>
</div>
""", unsafe_allow_html=True)

# Main Navigation
tab1, tab2, tab3 = st.tabs([
    "💰 현금흐름 예측",
    "🚨 흑자도산 위험도 진단",
    "🏦 정책자금 맞춤 추천",
])

with tab1:
    render_cashflow_tab()

with tab2:
    render_risk_tab()

with tab3:
    render_recommend_tab()

