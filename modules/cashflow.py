import pandas as pd
import numpy as np
import json
import io
import plotly.graph_objects as go
import plotly.express as px
import streamlit as st
from prophet import Prophet


# ──────────────────────────────────────────────
# 헬퍼: JSON → DataFrame
# ──────────────────────────────────────────────
def _load_json(source) -> dict:
    """파일 객체 또는 경로 문자열에서 JSON을 로드합니다."""
    if isinstance(source, str):
        with open(source, "r", encoding="utf-8") as f:
            return json.load(f)
    return json.load(source)


# ──────────────────────────────────────────────
# 핵심: 현금흐름 계산
# ──────────────────────────────────────────────
def build_cashflow(data: dict) -> pd.DataFrame:
    """
    JSON 데이터(invoices + loans)를 받아
    일별 net_cash_flow DataFrame을 반환합니다.
    """
    invoices = pd.DataFrame(data["invoices"])
    loans = pd.DataFrame(data["loans"])

    invoices["issue_date"] = pd.to_datetime(invoices["issue_date"])
    loans["resAccountTrDate"] = pd.to_datetime(loans["resAccountTrDate"])

    sales = (
        invoices[invoices["transaction_type"] == "매출"]
        .groupby("issue_date")["total_amount"]
        .sum()
    )
    purchases = (
        invoices[invoices["transaction_type"] == "매입"]
        .groupby("issue_date")["total_amount"]
        .sum()
    )
    loans["total_outflow"] = loans["resPrincipal"] + loans["resInterest"]

    all_dates = pd.date_range(invoices["issue_date"].min(), invoices["issue_date"].max())
    cf = pd.DataFrame({"date": all_dates})
    cf = cf.merge(sales.rename("inflow"), left_on="date", right_on="issue_date", how="left")
    cf = cf.merge(purchases.rename("purchase_outflow"), left_on="date", right_on="issue_date", how="left")

    loan_outflow = loans.groupby("resAccountTrDate")["total_outflow"].sum()
    cf = cf.merge(loan_outflow.rename("loan_outflow"), left_on="date", right_on="resAccountTrDate", how="left")

    cf.fillna(0, inplace=True)
    cf["net_cash_flow"] = cf["inflow"] - cf["purchase_outflow"] - cf["loan_outflow"]
    return cf[["date", "net_cash_flow", "inflow", "purchase_outflow", "loan_outflow"]]


# ──────────────────────────────────────────────
# Prophet 예측
# ──────────────────────────────────────────────
def run_prophet(cf: pd.DataFrame):
    """
    Prophet으로 이번 달 말까지 현금흐름을 예측합니다.
    Returns: (forecast_df, current_month_df, forecast_month_df, loan_schedule, message, loans_df)
    """
    df_prophet = cf[["date", "net_cash_flow"]].rename(columns={"date": "ds", "net_cash_flow": "y"})
    model = Prophet(daily_seasonality=True, interval_width=0.9)
    model.fit(df_prophet)

    end_of_month = pd.Timestamp.today().replace(day=1) + pd.offsets.MonthEnd(0)
    periods = max((end_of_month - cf["date"].max()).days, 0)
    future = model.make_future_dataframe(periods=periods)
    forecast = model.predict(future)

    today = pd.Timestamp.today().normalize()
    start_of_month = today.replace(day=1)

    current_month = cf[(cf["date"] >= start_of_month) & (cf["date"] <= today)].copy()
    current_month["cum_actual"] = current_month["net_cash_flow"].cumsum()

    forecast_month = forecast[
        (forecast["ds"] >= start_of_month) & (forecast["ds"] <= end_of_month)
    ]

    # 잔고 부족 계산
    future_dates = pd.date_range(today + pd.Timedelta(days=1), end_of_month)
    forecast_future = (
        forecast.set_index("ds").reindex(future_dates, method="nearest")["yhat"].fillna(0)
    )
    last_cum = current_month["cum_actual"].iloc[-1] if not current_month.empty else 0
    balance = last_cum + forecast_future.cumsum()
    insufficient = balance[balance < 0]

    if not insufficient.empty:
        first_day = insufficient.index[0]
        shortage = -int(insufficient.iloc[0])
        n_days = (first_day - today).days
        message = ("warning", f"⚠️ {n_days}일 뒤({first_day.strftime('%m/%d')})에 약 {shortage:,}원 부족할 수 있습니다. 미리 준비하세요!")
    else:
        message = ("success", "👍 이번 달 말까지 현금은 충분할 것으로 예상됩니다.")

    return forecast, current_month, forecast_month, message


# ──────────────────────────────────────────────
# Streamlit 렌더링
# ──────────────────────────────────────────────
def render_cashflow_tab():
    st.markdown("## 💰 현금흐름 예측")
    st.markdown(
        "매출·매입 세금계산서와 대출 상환 내역이 담긴 **JSON 파일**을 업로드하면, "
        "이번 달 말까지 현금 부족 여부를 예측합니다."
    )

    # ── 입력 방식 선택 ──────────────────────────
    col_opt1, col_opt2 = st.columns(2)
    use_sample = col_opt1.checkbox("📂 샘플 데이터 사용", value=True)
    uploaded = col_opt2.file_uploader(
        "또는 JSON 파일 직접 업로드",
        type=["json"],
        disabled=use_sample,
        help="invoices(issue_date, transaction_type, total_amount)와 loans(resAccountTrDate, resLoanKind, resPrincipal, resInterest) 키가 필요합니다.",
    )

    # ── 데이터 로드 ──────────────────────────────
    data_source = None
    if use_sample:
        try:
            data_source = "data/sample_codef_data.json"
            st.info("📌 샘플 데이터(2025년 1월 ~ 2026년 4월)를 사용 중입니다.")
        except Exception:
            st.error("샘플 파일을 찾을 수 없습니다. (`data/sample_codef_data.json`)")
            return
    elif uploaded:
        data_source = uploaded
    else:
        st.warning("샘플 데이터를 사용하거나 JSON 파일을 업로드해 주세요.")
        _show_json_format()
        return

    # ── 처리 ─────────────────────────────────────
    try:
        data = _load_json(data_source)
        cf = build_cashflow(data)
    except Exception as e:
        st.error(f"데이터 처리 중 오류가 발생했습니다: {e}")
        return

    with st.spinner("🔮 Prophet 모델 학습 중..."):
        try:
            forecast, current_month, forecast_month, message = run_prophet(cf)
        except Exception as e:
            st.error(f"예측 중 오류: {e}")
            return

    # ── 알림 메시지 ──────────────────────────────
    status, msg = message
    if status == "warning":
        st.warning(msg)
    else:
        st.success(msg)

    st.divider()

    # ── 차트 1: 이번 달 누적 현금 (실제) ─────────
    if not current_month.empty:
        st.markdown("### 📈 이번 달 누적 순현금 (실제)")
        fig1 = go.Figure()
        fig1.add_trace(go.Scatter(
            x=current_month["date"],
            y=current_month["cum_actual"] / 1e4,
            mode="lines+markers",
            line=dict(color="#00C896", width=3),
            marker=dict(size=6),
            name="누적 순현금",
            hovertemplate="%{x|%m-%d}<br>%{y:,.0f}만원<extra></extra>",
        ))
        fig1.add_hline(y=0, line_dash="dash", line_color="#FF4B4B", annotation_text="0원 기준선")
        fig1.update_layout(
            height=320,
            paper_bgcolor="rgba(0,0,0,0)",
            plot_bgcolor="rgba(0,0,0,0)",
            xaxis=dict(showgrid=False, tickformat="%m-%d"),
            yaxis=dict(showgrid=True, gridcolor="rgba(255,255,255,0.1)", title="누적 금액 (만원)"),
            legend=dict(orientation="h"),
            margin=dict(t=20, b=20),
        )
        st.plotly_chart(fig1, use_container_width=True)
    else:
        st.info("이번 달 실제 데이터가 없습니다.")

    # ── 차트 2: 이번 달 매출 예측 ────────────────
    st.markdown("### 🔮 이번 달 순현금 예측 (Prophet)")
    if not forecast_month.empty:
        fig2 = go.Figure()
        fig2.add_trace(go.Scatter(
            x=forecast_month["ds"],
            y=forecast_month["yhat"] / 1e4,
            mode="lines",
            line=dict(color="#4B9EFF", width=2, dash="dot"),
            name="예상 순현금",
            hovertemplate="%{x|%m-%d}<br>%{y:,.0f}만원<extra></extra>",
        ))
        fig2.add_trace(go.Scatter(
            x=pd.concat([forecast_month["ds"], forecast_month["ds"].iloc[::-1]]),
            y=pd.concat([forecast_month["yhat_upper"] / 1e4, forecast_month["yhat_lower"].iloc[::-1] / 1e4]),
            fill="toself",
            fillcolor="rgba(75,158,255,0.15)",
            line=dict(color="rgba(0,0,0,0)"),
            name="90% 신뢰구간",
            hoverinfo="skip",
        ))
        fig2.add_hline(y=0, line_dash="dash", line_color="#FF4B4B", annotation_text="0원 기준선")
        fig2.update_layout(
            height=320,
            paper_bgcolor="rgba(0,0,0,0)",
            plot_bgcolor="rgba(0,0,0,0)",
            xaxis=dict(showgrid=False, tickformat="%m-%d"),
            yaxis=dict(showgrid=True, gridcolor="rgba(255,255,255,0.1)", title="예상 금액 (만원)"),
            legend=dict(orientation="h"),
            margin=dict(t=20, b=20),
        )
        st.plotly_chart(fig2, use_container_width=True)

    # ── 차트 3: 대출 예정 ─────────────────────────
    loans_df = pd.DataFrame(data["loans"])
    loans_df["resAccountTrDate"] = pd.to_datetime(loans_df["resAccountTrDate"])
    loans_df["total_outflow"] = loans_df["resPrincipal"] + loans_df["resInterest"]

    today = pd.Timestamp.today().normalize()
    start_of_month = today.replace(day=1)
    end_of_month = today.replace(day=1) + pd.offsets.MonthEnd(0)

    loan_schedule = (
        loans_df[loans_df["resAccountTrDate"] >= start_of_month]
        .groupby(["resAccountTrDate", "resLoanKind"])["total_outflow"]
        .sum()
        .unstack(fill_value=0)
    )

    if not loan_schedule.empty:
        st.markdown("### 🏦 앞으로 나갈 대출 예정금액 (종류별)")
        loan_schedule_plot = loan_schedule / 1e4
        loan_schedule_plot.index = loan_schedule_plot.index.strftime("%m-%d")

        colors = ["#FF6B6B", "#FFB347", "#87CEEB", "#90EE90", "#DDA0DD"]
        fig3 = go.Figure()
        for i, col in enumerate(loan_schedule_plot.columns):
            fig3.add_trace(go.Bar(
                name=col,
                x=loan_schedule_plot.index,
                y=loan_schedule_plot[col],
                marker_color=colors[i % len(colors)],
                hovertemplate=f"{col}<br>%{{x}}: %{{y:,.0f}}만원<extra></extra>",
            ))
        fig3.update_layout(
            barmode="stack",
            height=300,
            paper_bgcolor="rgba(0,0,0,0)",
            plot_bgcolor="rgba(0,0,0,0)",
            xaxis=dict(showgrid=False),
            yaxis=dict(showgrid=True, gridcolor="rgba(255,255,255,0.1)", title="출금 금액 (만원)"),
            legend=dict(orientation="h"),
            margin=dict(t=20, b=20),
        )
        st.plotly_chart(fig3, use_container_width=True)
    else:
        st.info("이번 달 이후 예정된 대출 상환 내역이 없습니다.")

    # ── 원본 데이터 미리보기 ─────────────────────
    with st.expander("📊 원본 현금흐름 데이터 보기"):
        st.dataframe(
            cf.rename(columns={
                "date": "날짜",
                "net_cash_flow": "순현금흐름(원)",
                "inflow": "매출유입(원)",
                "purchase_outflow": "매입지출(원)",
                "loan_outflow": "대출상환(원)",
            }).tail(60),
            use_container_width=True,
        )


def _show_json_format():
    """JSON 데이터 형식 안내"""
    st.markdown("#### 📋 JSON 파일 형식")
    st.code("""{
  "invoices": [
    {
      "issue_date": "2026-04-01",
      "transaction_type": "매출",  // 또는 "매입"
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
