"""
src/ui/risk_tab.py
"""
from __future__ import annotations

import pandas as pd
import plotly.graph_objects as go
import streamlit as st

from src.config import (
    CHART_GRID_COLOR,
    CHART_TRANSPARENT_LAYOUT,
    REGION_COL_CANDIDATES,
    SECTOR_COL_CANDIDATES,
    SME_DATA_PATH,
)
from src.data.loaders import find_column, load_sme_data
from src.domain.risk import RiskError, RiskResult, calculate_risk


def render_risk_tab() -> None:
    """탭2 전체를 렌더링합니다."""
    st.markdown("## 🚨 흑자도산 위험도 진단")
    st.markdown(
        "매출은 발생했지만 **매출채권 회수가 늦어** 현금이 부족해지는 '흑자도산' 위험도를 진단합니다. "
        "업종·지역별 업계 중앙값과 비교하여 등급을 부여합니다."
    )

    df = _load_sme_df()
    if df is None:
        return

    result = _render_input_form(df)
    if result is None:
        _render_concept_info()
        return

    if isinstance(result, RiskError):
        st.error(result.message)
        return

    st.divider()
    _render_summary_metrics(result)
    _render_gauge_chart(result)
    _render_days_comparison(result)
    _render_advice_message(result)


# ── 데이터 로드 ────────────────────────────────────

def _load_sme_df() -> pd.DataFrame | None:
    try:
        return load_sme_data(str(SME_DATA_PATH))
    except Exception as e:
        st.error(f"sme_data.csv 로드 실패: {e}")
        return None


# ── 입력 폼 ────────────────────────────────────────

def _render_input_form(df: pd.DataFrame) -> RiskResult | RiskError | None:
    """
    사용자 입력 폼을 렌더링하고 제출 시 RiskResult/RiskError를 반환합니다.
    미제출 상태면 None을 반환합니다.
    """
    region_col = find_column(df, REGION_COL_CANDIDATES) or df.columns[0]
    sector_col = find_column(df, SECTOR_COL_CANDIDATES) or df.columns[1]

    regions = sorted(df[region_col].dropna().unique().tolist())
    sectors = sorted(df[sector_col].dropna().unique().tolist())

    with st.form("risk_form"):
        st.markdown("#### 📝 내 사업 정보 입력")
        col1, col2 = st.columns(2)
        region = col1.selectbox(
            "📍 지역 (시도)", regions,
            index=regions.index("전국") if "전국" in regions else 0,
        )
        sector = col2.selectbox("🏭 업종 대분류", sectors)

        col3, col4 = st.columns(2)
        my_sales = col3.number_input(
            "💵 연매출액 (원)",
            min_value=0,
            value=300_000_000,
            step=10_000_000,
            help="최근 1년간 총 매출액을 입력하세요.",
        )
        my_ar_amount = col4.number_input(
            "📄 매출채권 잔액 (원)",
            min_value=1,
            value=40_000_000,
            step=1_000_000,
            help="현재 받지 못한 매출채권(외상매출금) 잔액을 입력하세요.",
        )
        submitted = st.form_submit_button("🔍 위험도 진단하기", use_container_width=True)

    if not submitted:
        return None

    return calculate_risk(df, region, sector, float(my_sales), float(my_ar_amount))


# ── 결과 UI 컴포넌트 ───────────────────────────────

def _render_summary_metrics(result: RiskResult) -> None:
    st.markdown(f"#### {result.emoji} [{result.region} / {result.sector}] 진단 결과")
    col1, col2, col3 = st.columns(3)
    col1.metric("내 매출채권 회전율",  f"{result.my_turnover:.2f}회")
    col2.metric("업계 중앙값 회전율",  f"{result.industry_turnover:.2f}회")
    col3.metric(
        "업계 대비 비율",
        f"{result.ratio:.2f}배",
        delta=f"{(result.ratio - 1) * 100:+.1f}%",
        delta_color="normal",
    )


def _render_gauge_chart(result: RiskResult) -> None:
    fig = go.Figure(go.Indicator(
        mode="gauge+number",
        value=result.gauge_value,
        number={"suffix": " pt", "font": {"size": 30}},
        gauge={
            "axis":      {"range": [0, 100], "tickwidth": 1, "tickcolor": "white"},
            "bar":       {"color": result.color},
            "bgcolor":   "rgba(0,0,0,0)",
            "borderwidth": 0,
            "steps": [
                {"range": [0, 25],   "color": "rgba(255,75,75,0.15)"},
                {"range": [25, 50],  "color": "rgba(255,140,0,0.15)"},
                {"range": [50, 75],  "color": "rgba(255,215,0,0.15)"},
                {"range": [75, 100], "color": "rgba(0,200,150,0.15)"},
            ],
            "threshold": {
                "line":      {"color": result.color, "width": 4},
                "thickness": 0.75,
                "value":     result.gauge_value,
            },
        },
        title={"text": f"위험도 지수 — {result.label}", "font": {"size": 18}},
    ))
    fig.update_layout(
        height=280,
        paper_bgcolor="rgba(0,0,0,0)",
        font={"color": "white"},
        margin=dict(t=60, b=0, l=30, r=30),
    )
    st.plotly_chart(fig, use_container_width=True)


def _render_days_comparison(result: RiskResult) -> None:
    col_left, col_right = st.columns(2)

    with col_left:
        st.markdown("##### 📅 평균 회수기간 비교")
        st.dataframe(
            pd.DataFrame({
                "구분":       ["내 사업", "업계 중앙값"],
                "회전율(회)":  [f"{result.my_turnover:.2f}", f"{result.industry_turnover:.2f}"],
                "회수기간(일)": [f"{result.my_days:.1f}일", f"{result.industry_days:.1f}일"],
            }),
            hide_index=True,
            use_container_width=True,
        )

    with col_right:
        fig = go.Figure(go.Bar(
            x=["내 사업", "업계 중앙값"],
            y=[result.my_days, result.industry_days],
            marker_color=[result.color, "#4B9EFF"],
            text=[f"{result.my_days:.1f}일", f"{result.industry_days:.1f}일"],
            textposition="outside",
        ))
        fig.update_layout(
            height=220,
            xaxis=dict(showgrid=False),
            yaxis=dict(showgrid=True, gridcolor=CHART_GRID_COLOR, title="회수기간(일)"),
            **CHART_TRANSPARENT_LAYOUT,
        )
        st.plotly_chart(fig, use_container_width=True)


def _render_advice_message(result: RiskResult) -> None:
    getattr(st, result.st_func)(
        f"**{result.emoji} {result.label}**: {result.advice}"
    )


def _render_concept_info() -> None:
    with st.expander("💡 흑자도산이란?"):
        st.markdown("""
**흑자도산**이란 장부상 이익이 발생함에도 불구하고, **실제 현금이 부족**하여 기업이 도산하는 현상입니다.

| 지표 | 설명 |
|---|---|
| **매출채권 회전율** | 연매출 ÷ 매출채권잔액. 높을수록 빨리 돈을 받는 것 |
| **평균 회수기간** | 365 ÷ 회전율. 낮을수록 좋음 |
| **업계 중앙값** | 동일 업종·지역 기업들의 중위값 기준 |

> 예시: 매출채권 회전율이 3회라면 평균 122일 만에 대금을 회수한다는 의미입니다.
        """)
