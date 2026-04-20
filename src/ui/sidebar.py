"""
src/ui/sidebar.py
"""
import streamlit as st


def render_sidebar() -> None:
    """사이드바 전체를 렌더링합니다."""
    with st.sidebar:
        _render_logo()
        st.divider()
        _render_concept_card()
        st.divider()
        _render_service_guide()
        st.divider()
        _render_disclaimer()


# ── 내부 컴포넌트 ──────────────────────────────────

def _render_logo() -> None:
    st.markdown("""
    <div style="text-align:center; padding: 10px 0 20px 0;">
        <div style="font-size: 3rem;">🛡️</div>
        <h2 style="color: #00C896; margin: 0; font-size: 1.2rem; font-weight: 700;">흑자도산 방지</h2>
        <p style="color: rgba(255,255,255,0.4); font-size: 0.8rem; margin: 4px 0 0 0;">
            소상공인 현금흐름 관리 대시보드
        </p>
    </div>
    """, unsafe_allow_html=True)


def _render_concept_card() -> None:
    st.markdown("### 📌 흑자도산이란?")
    st.markdown("""
    <div style="
        background: rgba(255,75,75,0.1);
        border-left: 3px solid #FF4B4B;
        border-radius: 0 8px 8px 0;
        padding: 12px 14px;
        font-size: 0.85rem;
        color: rgba(255,255,255,0.8);
        line-height: 1.6;
    ">
        매출·이익은 발생하지만<br>
        <b>매출채권 회수가 늦어</b><br>
        실제 현금이 부족해지는 현상
    </div>
    """, unsafe_allow_html=True)


def _render_service_guide() -> None:
    st.markdown("### 🗺️ 서비스 안내")
    st.markdown("""
    <div style="font-size: 0.85rem; color: rgba(255,255,255,0.7); line-height: 2;">
        💰 <b>탭 1</b> — 현금흐름 예측<br>
        &nbsp;&nbsp;&nbsp;↳ Prophet AI 기반 예측<br><br>
        🚨 <b>탭 2</b> — 위험도 진단<br>
        &nbsp;&nbsp;&nbsp;↳ 업종별 매출채권 비교<br><br>
        🏦 <b>탭 3</b> — 정책자금 추천<br>
        &nbsp;&nbsp;&nbsp;↳ LDA 토픽 매칭 추천
    </div>
    """, unsafe_allow_html=True)


def _render_disclaimer() -> None:
    st.markdown("""
    <p style="font-size: 0.75rem; color: rgba(255,255,255,0.25); text-align: center;">
        데이터 출처: 소상공인시장진흥공단(SEMAS)<br>
        본 서비스는 참고용이며 법적 책임을 지지 않습니다.
    </p>
    """, unsafe_allow_html=True)
