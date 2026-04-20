"""
src/domain/cashflow.py
"""
from __future__ import annotations

from dataclasses import dataclass

import pandas as pd
from prophet import Prophet

from src.config import PROPHET_DAILY_SEASONALITY, PROPHET_INTERVAL_WIDTH


@dataclass
class CashflowForecastResult:
    """Prophet 예측 결과를 담는 데이터 클래스."""
    forecast:       pd.DataFrame
    current_month:  pd.DataFrame   # 이번 달 실제 누적 데이터
    forecast_month: pd.DataFrame   # 이번 달 예측 데이터
    is_insufficient: bool
    shortage_amount: int            # 부족 금액 (원). is_insufficient=False면 0
    days_until_shortage: int        # 부족 예상까지 남은 일수
    shortage_date: pd.Timestamp | None


def build_cashflow(data: dict) -> tuple[pd.DataFrame, pd.DataFrame]:
    """
    JSON 데이터(invoices + loans)를 받아 일별 현금흐름 DataFrame을 반환합니다.

    Args:
        data: {"invoices": [...], "loans": [...]} 형태의 dict

    Returns:
        (cashflow_df, loans_df) 튜플
        cashflow_df 컬럼: date, net_cash_flow, inflow, purchase_outflow, loan_outflow
        loans_df: 원본 대출 DataFrame (loan_schedule 차트용)
    """
    invoices = pd.DataFrame(data["invoices"])
    loans_df = pd.DataFrame(data["loans"])

    invoices["issue_date"]       = pd.to_datetime(invoices["issue_date"])
    loans_df["resAccountTrDate"] = pd.to_datetime(loans_df["resAccountTrDate"])

    # 매출 / 매입 일별 집계
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

    loans_df["total_outflow"] = loans_df["resPrincipal"] + loans_df["resInterest"]
    loan_outflow = loans_df.groupby("resAccountTrDate")["total_outflow"].sum()

    # 날짜 범위 생성 후 병합
    all_dates = pd.date_range(invoices["issue_date"].min(), invoices["issue_date"].max())
    cf = pd.DataFrame({"date": all_dates})
    cf = cf.merge(sales.rename("inflow"),           left_on="date", right_index=True, how="left")
    cf = cf.merge(purchases.rename("purchase_outflow"), left_on="date", right_index=True, how="left")
    cf = cf.merge(loan_outflow.rename("loan_outflow"),  left_on="date", right_index=True, how="left")

    cf.fillna(0, inplace=True)
    cf["net_cash_flow"] = cf["inflow"] - cf["purchase_outflow"] - cf["loan_outflow"]

    return cf[["date", "net_cash_flow", "inflow", "purchase_outflow", "loan_outflow"]], loans_df


def run_prophet_forecast(cf: pd.DataFrame) -> CashflowForecastResult:
    """
    Prophet으로 이번 달 말까지 순현금흐름을 예측하고 부족 여부를 진단합니다.

    Args:
        cf: build_cashflow()가 반환한 cashflow DataFrame

    Returns:
        CashflowForecastResult 인스턴스
    """
    df_prophet = cf[["date", "net_cash_flow"]].rename(
        columns={"date": "ds", "net_cash_flow": "y"}
    )

    model = Prophet(
        daily_seasonality=PROPHET_DAILY_SEASONALITY,
        interval_width=PROPHET_INTERVAL_WIDTH,
    )
    model.fit(df_prophet)

    today          = pd.Timestamp.today().normalize()
    start_of_month = today.replace(day=1)
    end_of_month   = today.replace(day=1) + pd.offsets.MonthEnd(0)

    periods = max((end_of_month - cf["date"].max()).days, 0)
    forecast = model.predict(model.make_future_dataframe(periods=periods))

    # 이번 달 실제 데이터
    current_month = cf[
        (cf["date"] >= start_of_month) & (cf["date"] <= today)
    ].copy()
    current_month["cum_actual"] = current_month["net_cash_flow"].cumsum()

    # 이번 달 예측 데이터
    forecast_month = forecast[
        (forecast["ds"] >= start_of_month) & (forecast["ds"] <= end_of_month)
    ]

    # 잔고 부족 감지
    future_dates    = pd.date_range(today + pd.Timedelta(days=1), end_of_month)
    forecast_future = (
        forecast.set_index("ds")
        .reindex(future_dates, method="nearest")["yhat"]
        .fillna(0)
    )
    last_cum    = current_month["cum_actual"].iloc[-1] if not current_month.empty else 0
    balance     = last_cum + forecast_future.cumsum()
    insufficient = balance[balance < 0]

    if not insufficient.empty:
        first_day = insufficient.index[0]
        return CashflowForecastResult(
            forecast=forecast,
            current_month=current_month,
            forecast_month=forecast_month,
            is_insufficient=True,
            shortage_amount=-int(insufficient.iloc[0]),
            days_until_shortage=(first_day - today).days,
            shortage_date=first_day,
        )

    return CashflowForecastResult(
        forecast=forecast,
        current_month=current_month,
        forecast_month=forecast_month,
        is_insufficient=False,
        shortage_amount=0,
        days_until_shortage=0,
        shortage_date=None,
    )


def build_loan_schedule(loans_df: pd.DataFrame) -> pd.DataFrame:
    """
    이번 달 이후 예정된 대출 상환 일정을 종류별로 집계합니다.

    Args:
        loans_df: build_cashflow()가 반환한 loans DataFrame

    Returns:
        (날짜 × 대출종류) pivot DataFrame. 만원 단위.
    """
    today          = pd.Timestamp.today().normalize()
    start_of_month = today.replace(day=1)

    schedule = (
        loans_df[loans_df["resAccountTrDate"] >= start_of_month]
        .groupby(["resAccountTrDate", "resLoanKind"])["total_outflow"]
        .sum()
        .unstack(fill_value=0)
    )

    if not schedule.empty:
        schedule = schedule / 1e4  # 만원 단위
        schedule.index = schedule.index.strftime("%m-%d")

    return schedule
