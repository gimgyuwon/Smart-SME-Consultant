import pandas as pd
import numpy as np
import plotly.graph_objects as go
import streamlit as st

# ──────────────────────────────────────────────
# SME 데이터 로드 (탭 전체 공유)
# ──────────────────────────────────────────────
@st.cache_data
def load_sme_data(path: str = "data/sme_data.csv") -> pd.DataFrame:
    """
    sme_data.csv 를 읽어 DataFrame으로 반환합니다.
    인코딩: UTF-16 (BOM 포함), 탭 구분자
    컬럼: 시도명, 업종 대분류, 중앙값 매출채권회전율 (핵심 3개)
    """
    df = pd.read_csv(path, encoding="utf-16", sep="\t")
    # 컬럼명 정리 (앞뒤 공백 제거)
    df.columns = df.columns.str.strip()
    # 시도명 빈칸 → '전국'
    if "시도명" in df.columns:
        df["시도명"] = df["시도명"].fillna("전국").str.strip()
    return df


# ──────────────────────────────────────────────
# 핵심: 위험도 계산
# ──────────────────────────────────────────────
def calculate_risk(df: pd.DataFrame, region: str, sector: str,
                   my_sales: float, my_ar_amount: float) -> dict:
    """
    매출채권 회전율 기반 흑자도산 위험도를 계산합니다.

    Returns:
        dict with keys: my_turnover, industry_turnover, ratio,
                        my_days, industry_days, risk_level, risk_color,
                        risk_emoji, advice, region, sector
    """
    # 컬럼명 탐색 (유연하게 처리)
    turnover_col = _find_column(df, ["중앙값 매출채권회전율", "매출채권회전율", "회전율"])
    region_col   = _find_column(df, ["시도명", "지역"])
    sector_col   = _find_column(df, ["업종 대분류", "업종대분류", "업종"])

    if not all([turnover_col, region_col, sector_col]):
        return {"error": f"필요한 컬럼을 찾을 수 없습니다. 컬럼 목록: {df.columns.tolist()}"}

    # 업계 중앙값 조회
    cond = (df[region_col] == region) & (df[sector_col] == sector)
    row = df[cond]

    if row.empty:
        # 전국 fallback
        cond_national = (df[region_col] == "전국") & (df[sector_col] == sector)
        row = df[cond_national]
        if row.empty:
            return {"error": f"'{region} / {sector}' 데이터가 없습니다."}
        region = f"{region}(→전국 평균 사용)"

    industry_turnover_raw = row[turnover_col].values[0]

    # 문자열(%) 처리
    if isinstance(industry_turnover_raw, str):
        industry_turnover_raw = float(industry_turnover_raw.replace("%", "").strip())
    else:
        industry_turnover_raw = float(industry_turnover_raw)

    # CSV 값이 회전율 자체인지 % 비율인지 판별
    # guide_code.md 기준: sme_data.csv 컬럼이 "중앙값 매출채권회전율"으로 실제 회전율(예: 8.4)
    # 값이 소수라면 그대로, 음수면 절댓값 처리
    industry_turnover = abs(industry_turnover_raw)
    if industry_turnover == 0:
        return {"error": "업계 중앙값 회전율이 0입니다."}

    my_turnover = my_sales / my_ar_amount
    ratio = my_turnover / industry_turnover

    # 위험도 등급
    if ratio >= 1.2:
        risk_level = "매우 양호"
        risk_color = "#00C896"
        risk_emoji = "🟢"
        gauge_value = min(ratio * 50, 100)
        advice = "회전율이 업계 대비 매우 높습니다. 현금흐름이 안정적입니다."
    elif ratio >= 0.8:
        risk_level = "보통"
        risk_color = "#FFD700"
        risk_emoji = "🟡"
        gauge_value = 65
        advice = "업계 평균 수준입니다. 지속적인 모니터링을 권장합니다."
    elif ratio >= 0.5:
        risk_level = "주의"
        risk_color = "#FF8C00"
        risk_emoji = "🟠"
        gauge_value = 40
        advice = "회수 속도가 업계 대비 느립니다. 매출채권 회수 관리가 필요합니다."
    else:
        risk_level = "위험"
        risk_color = "#FF4B4B"
        risk_emoji = "🔴"
        gauge_value = 15
        advice = "회수 지연으로 현금흐름 악화 가능성이 높습니다. 즉각적인 조치가 필요합니다."

    my_days = 365 / my_turnover
    industry_days = 365 / industry_turnover

    return {
        "my_turnover": my_turnover,
        "industry_turnover": industry_turnover,
        "ratio": ratio,
        "my_days": my_days,
        "industry_days": industry_days,
        "risk_level": risk_level,
        "risk_color": risk_color,
        "risk_emoji": risk_emoji,
        "gauge_value": gauge_value,
        "advice": advice,
        "region": region,
        "sector": sector,
    }


def _find_column(df: pd.DataFrame, candidates: list) -> str | None:
    """후보 컬럼명 목록 중 실제 존재하는 첫 번째 컬럼을 반환합니다."""
    for c in candidates:
        if c in df.columns:
            return c
    return None


# ──────────────────────────────────────────────
# Streamlit 렌더링
# ──────────────────────────────────────────────
def render_risk_tab():
    st.markdown("## 🚨 흑자도산 위험도 진단")
    st.markdown(
        "매출은 발생했지만 **매출채권 회수가 늦어** 현금이 부족해지는 '흑자도산' 위험도를 진단합니다. "
        "업종·지역별 업계 중앙값과 비교하여 등급을 부여합니다."
    )

    # ── SME 데이터 로드 ──────────────────────────
    sme_path = "data/sme_data.csv"
    try:
        df = load_sme_data(sme_path)
    except Exception as e:
        st.error(f"sme_data.csv 로드 실패: {e}")
        return

    region_col = _find_column(df, ["시도명", "지역"]) or df.columns[0]
    sector_col = _find_column(df, ["업종 대분류", "업종대분류", "업종"]) or df.columns[1]

    regions = sorted(df[region_col].dropna().unique().tolist())
    sectors = sorted(df[sector_col].dropna().unique().tolist())

    # ── 입력 폼 ──────────────────────────────────
    with st.form("risk_form"):
        st.markdown("#### 📝 내 사업 정보 입력")
        col1, col2 = st.columns(2)
        region = col1.selectbox("📍 지역 (시도)", regions, index=regions.index("전국") if "전국" in regions else 0)
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
        _show_concept_info()
        return

    # ── 계산 ─────────────────────────────────────
    result = calculate_risk(df, region, sector, float(my_sales), float(my_ar_amount))

    if "error" in result:
        st.error(result["error"])
        return

    st.divider()

    # ── 결과 요약 카드 ────────────────────────────
    st.markdown(f"#### {result['risk_emoji']} [{result['region']} / {result['sector']}] 진단 결과")

    col_a, col_b, col_c = st.columns(3)
    col_a.metric("내 매출채권 회전율", f"{result['my_turnover']:.2f}회")
    col_b.metric("업계 중앙값 회전율", f"{result['industry_turnover']:.2f}회")
    col_c.metric(
        "업계 대비 비율",
        f"{result['ratio']:.2f}배",
        delta=f"{(result['ratio']-1)*100:+.1f}%",
        delta_color="normal",
    )

    # ── 게이지 차트 ───────────────────────────────
    fig_gauge = go.Figure(go.Indicator(
        mode="gauge+number",
        value=result["gauge_value"],
        number={"suffix": " pt", "font": {"size": 30}},
        gauge={
            "axis": {"range": [0, 100], "tickwidth": 1, "tickcolor": "white"},
            "bar": {"color": result["risk_color"]},
            "bgcolor": "rgba(0,0,0,0)",
            "borderwidth": 0,
            "steps": [
                {"range": [0, 25],  "color": "rgba(255,75,75,0.15)"},
                {"range": [25, 50], "color": "rgba(255,140,0,0.15)"},
                {"range": [50, 75], "color": "rgba(255,215,0,0.15)"},
                {"range": [75, 100],"color": "rgba(0,200,150,0.15)"},
            ],
            "threshold": {
                "line": {"color": result["risk_color"], "width": 4},
                "thickness": 0.75,
                "value": result["gauge_value"],
            },
        },
        title={"text": f"위험도 지수 — {result['risk_level']}", "font": {"size": 18}},
    ))
    fig_gauge.update_layout(
        height=280,
        paper_bgcolor="rgba(0,0,0,0)",
        font={"color": "white"},
        margin=dict(t=60, b=0, l=30, r=30),
    )
    st.plotly_chart(fig_gauge, use_container_width=True)

    # ── 회수기간 비교 ─────────────────────────────
    col_d, col_e = st.columns(2)
    with col_d:
        st.markdown("##### 📅 평균 회수기간 비교")
        compare_df = pd.DataFrame({
            "구분": ["내 사업", "업계 중앙값"],
            "회전율(회)": [f"{result['my_turnover']:.2f}", f"{result['industry_turnover']:.2f}"],
            "회수기간(일)": [f"{result['my_days']:.1f}일", f"{result['industry_days']:.1f}일"],
        })
        st.dataframe(compare_df, hide_index=True, use_container_width=True)

    with col_e:
        # 회수기간 바 차트
        fig_bar = go.Figure(go.Bar(
            x=["내 사업", "업계 중앙값"],
            y=[result["my_days"], result["industry_days"]],
            marker_color=[result["risk_color"], "#4B9EFF"],
            text=[f"{result['my_days']:.1f}일", f"{result['industry_days']:.1f}일"],
            textposition="outside",
        ))
        fig_bar.update_layout(
            height=220,
            paper_bgcolor="rgba(0,0,0,0)",
            plot_bgcolor="rgba(0,0,0,0)",
            yaxis=dict(showgrid=True, gridcolor="rgba(255,255,255,0.1)", title="회수기간(일)"),
            xaxis=dict(showgrid=False),
            margin=dict(t=20, b=20),
            font=dict(color="white"),
        )
        st.plotly_chart(fig_bar, use_container_width=True)

    # ── 조언 메시지 ───────────────────────────────
    advice_color_map = {
        "매우 양호": "success",
        "보통": "info",
        "주의": "warning",
        "위험": "error",
    }
    getattr(st, advice_color_map[result["risk_level"]])(
        f"**{result['risk_emoji']} {result['risk_level']}**: {result['advice']}"
    )


def _show_concept_info():
    """흑자도산 개념 설명"""
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
