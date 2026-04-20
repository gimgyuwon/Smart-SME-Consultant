"""
src/ui/cashflow_tab.py
"""
from __future__ import annotations

import pandas as pd
import plotly.graph_objects as go
import streamlit as st

from src.config import CHART_GRID_COLOR, CHART_TRANSPARENT_LAYOUT, LOAN_CHART_COLORS, SAMPLE_JSON_PATH
from src.data.loaders import load_json
from src.domain.cashflow import (
    CashflowForecastResult,
    build_cashflow,
    build_loan_schedule,
    run_prophet_forecast,
)


def render_cashflow_tab() -> None:
    """탭1 전체를 렌더링합니다."""
    st.markdown("## 💰 현금흐름 예측")
    st.markdown(
        "매출·매입 세금계산서와 대출 상환 내역이 담긴 **JSON 파일**을 업로드하면, "
        "이번 달 말까지 현금 부족 여부를 예측합니다."
    )

    data = _load_data_from_ui()
    if data is None:
        return

    cf, loans_df = _process_data(data)
    if cf is None:
        return

    result = _run_forecast(cf)
    if result is None:
        return

    _render_alert(result)
    st.divider()
    _render_cumulative_chart(result.current_month)
    _render_forecast_chart(result.forecast_month)
    _render_loan_schedule_chart(loans_df)
    _render_raw_data_expander(cf)


# ── 데이터 로드 ────────────────────────────────────

def _load_data_from_ui() -> dict | None:
    """UI 입력을 받아 JSON 데이터를 반환합니다. 실패 시 None."""
    col1, col2 = st.columns(2)
    use_sample = col1.checkbox("📂 샘플 데이터 사용", value=True)
    uploaded   = col2.file_uploader(
        "또는 JSON 파일 직접 업로드",
        type=["json"],
        disabled=use_sample,
        help=(
            "invoices(issue_date, transaction_type, total_amount)와 "
            "loans(resAccountTrDate, resLoanKind, resPrincipal, resInterest) 키가 필요합니다."
        ),
    )

    if use_sample:
        st.info("📌 샘플 데이터(2025년 1월 ~ 2026년 4월)를 사용 중입니다.")
        source = str(SAMPLE_JSON_PATH)
    elif uploaded:
        source = uploaded
    else:
        st.warning("샘플 데이터를 사용하거나 JSON 파일을 업로드해 주세요.")
        _render_json_format_guide()
        return None

    try:
        return load_json(source)
    except Exception as e:
        st.error(f"파일 로드 실패: {e}")
        return None


def _process_data(data: dict):
    """현금흐름 DataFrame을 생성합니다. 실패 시 (None, None)."""
    try:
        return build_cashflow(data)
    except Exception as e:
        st.error(f"데이터 처리 중 오류: {e}")
        return None, None


def _run_forecast(cf: pd.DataFrame) -> CashflowForecastResult | None:
    """Prophet 예측을 실행합니다. 실패 시 None."""
    with st.spinner("🔮 Prophet 모델 학습 중..."):
        try:
            return run_prophet_forecast(cf)
        except Exception as e:
            st.error(f"예측 중 오류: {e}")
            return None


# ── UI 컴포넌트 ────────────────────────────────────

def _render_alert(result: CashflowForecastResult) -> None:
    if result.is_insufficient:
        st.warning(
            f"⚠️ {result.days_until_shortage}일 뒤"
            f"({result.shortage_date.strftime('%m/%d')})에 "
            f"약 {result.shortage_amount:,}원 부족할 수 있습니다. 미리 준비하세요!"
        )
    else:
        st.success("👍 이번 달 말까지 현금은 충분할 것으로 예상됩니다.")


def _render_cumulative_chart(current_month: pd.DataFrame) -> None:
    st.markdown("### 📈 이번 달 누적 순현금 (실제)")
    if current_month.empty:
        st.info("이번 달 실제 데이터가 없습니다.")
        return

    fig = go.Figure()
    fig.add_trace(go.Scatter(
        x=current_month["date"],
        y=current_month["cum_actual"] / 1e4,
        mode="lines+markers",
        line=dict(color="#00C896", width=3),
        marker=dict(size=6),
        name="누적 순현금",
        hovertemplate="%{x|%m-%d}<br>%{y:,.0f}만원<extra></extra>",
    ))
    fig.add_hline(y=0, line_dash="dash", line_color="#FF4B4B", annotation_text="0원 기준선")
    fig.update_layout(
        height=320,
        xaxis=dict(showgrid=False, tickformat="%m-%d"),
        yaxis=dict(showgrid=True, gridcolor=CHART_GRID_COLOR, title="누적 금액 (만원)"),
        legend=dict(orientation="h"),
        **CHART_TRANSPARENT_LAYOUT,
    )
    st.plotly_chart(fig, use_container_width=True)


def _render_forecast_chart(forecast_month: pd.DataFrame) -> None:
    st.markdown("### 🔮 이번 달 순현금 예측 (Prophet)")
    if forecast_month.empty:
        return

    fig = go.Figure()
    fig.add_trace(go.Scatter(
        x=forecast_month["ds"],
        y=forecast_month["yhat"] / 1e4,
        mode="lines",
        line=dict(color="#4B9EFF", width=2, dash="dot"),
        name="예상 순현금",
        hovertemplate="%{x|%m-%d}<br>%{y:,.0f}만원<extra></extra>",
    ))
    fig.add_trace(go.Scatter(
        x=pd.concat([forecast_month["ds"], forecast_month["ds"].iloc[::-1]]),
        y=pd.concat([
            forecast_month["yhat_upper"] / 1e4,
            forecast_month["yhat_lower"].iloc[::-1] / 1e4,
        ]),
        fill="toself",
        fillcolor="rgba(75,158,255,0.15)",
        line=dict(color="rgba(0,0,0,0)"),
        name="90% 신뢰구간",
        hoverinfo="skip",
    ))
    fig.add_hline(y=0, line_dash="dash", line_color="#FF4B4B", annotation_text="0원 기준선")
    fig.update_layout(
        height=320,
        xaxis=dict(showgrid=False, tickformat="%m-%d"),
        yaxis=dict(showgrid=True, gridcolor=CHART_GRID_COLOR, title="예상 금액 (만원)"),
        legend=dict(orientation="h"),
        **CHART_TRANSPARENT_LAYOUT,
    )
    st.plotly_chart(fig, use_container_width=True)


def _render_loan_schedule_chart(loans_df: pd.DataFrame) -> None:
    schedule = build_loan_schedule(loans_df)
    if schedule.empty:
        st.info("이번 달 이후 예정된 대출 상환 내역이 없습니다.")
        return

    st.markdown("### 🏦 앞으로 나갈 대출 예정금액 (종류별)")
    fig = go.Figure()
    for i, col in enumerate(schedule.columns):
        fig.add_trace(go.Bar(
            name=col,
            x=schedule.index,
            y=schedule[col],
            marker_color=LOAN_CHART_COLORS[i % len(LOAN_CHART_COLORS)],
            hovertemplate=f"{col}<br>%{{x}}: %{{y:,.0f}}만원<extra></extra>",
        ))
    fig.update_layout(
        barmode="stack",
        height=300,
        xaxis=dict(showgrid=False),
        yaxis=dict(showgrid=True, gridcolor=CHART_GRID_COLOR, title="출금 금액 (만원)"),
        legend=dict(orientation="h"),
        **CHART_TRANSPARENT_LAYOUT,
    )
    st.plotly_chart(fig, use_container_width=True)


def _render_raw_data_expander(cf: pd.DataFrame) -> None:
    with st.expander("📊 원본 현금흐름 데이터 보기"):
        st.dataframe(
            cf.rename(columns={
                "date":             "날짜",
                "net_cash_flow":    "순현금흐름(원)",
                "inflow":           "매출유입(원)",
                "purchase_outflow": "매입지출(원)",
                "loan_outflow":     "대출상환(원)",
            }).tail(60),
            use_container_width=True,
        )


def _render_json_format_guide() -> None:
    st.markdown("#### 📋 JSON 파일 형식")
    st.code("""{
  "invoices": [
    {
      "issue_date": "2026-04-01",
      "transaction_type": "매출",
      "total_amount": 3000000
    }
  ],
  "loans": [
    {
      "resAccountTrDate": "2026-04-15",
      "resLoanKind": "운전자금대출",
      "resPrincipal": 300000,
      "resInterest": 37000
    }
  ]
}""", language="json")
