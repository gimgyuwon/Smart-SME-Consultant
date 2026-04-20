"""
src/domain/risk.py
"""
from __future__ import annotations

from dataclasses import dataclass, field

import pandas as pd

from src.config import (
    REGION_COL_CANDIDATES,
    RISK_LEVELS,
    RISK_THRESHOLDS,
    SECTOR_COL_CANDIDATES,
    TURNOVER_COL_CANDIDATES,
)
from src.data.loaders import find_column


@dataclass
class RiskResult:
    """위험도 진단 결과를 담는 데이터 클래스."""
    region:              str
    sector:              str
    my_turnover:         float
    industry_turnover:   float
    ratio:               float
    my_days:             float
    industry_days:       float
    risk_key:            str          # config.RISK_LEVELS의 키 ("very_good" | "normal" | "caution" | "danger")
    label:               str
    color:               str
    emoji:               str
    gauge_value:         float
    advice:              str
    st_func:             str          # streamlit 알림 함수 이름


@dataclass
class RiskError:
    """진단 실패 정보."""
    message: str


def _resolve_industry_turnover(raw_value) -> float:
    """
    CSV에서 읽어온 회전율 원시값을 float으로 변환합니다.
    문자열 퍼센트(%) 포함 여부를 처리하고 절댓값을 반환합니다.
    """
    if isinstance(raw_value, str):
        raw_value = float(raw_value.replace("%", "").strip())
    return abs(float(raw_value))


def _classify_risk(ratio: float) -> str:
    """비율에 따라 위험도 키를 반환합니다."""
    if ratio >= RISK_THRESHOLDS["very_good"]:
        return "very_good"
    if ratio >= RISK_THRESHOLDS["normal"]:
        return "normal"
    if ratio >= RISK_THRESHOLDS["caution"]:
        return "caution"
    return "danger"


def calculate_risk(
    df: pd.DataFrame,
    region: str,
    sector: str,
    my_sales: float,
    my_ar_amount: float,
) -> RiskResult | RiskError:
    """
    매출채권 회전율 기반 흑자도산 위험도를 계산합니다.

    Args:
        df:           sme_data DataFrame
        region:       시도명
        sector:       업종 대분류
        my_sales:     내 연매출 (원)
        my_ar_amount: 내 매출채권 잔액 (원)

    Returns:
        성공 시 RiskResult, 실패 시 RiskError
    """
    turnover_col = find_column(df, TURNOVER_COL_CANDIDATES)
    region_col   = find_column(df, REGION_COL_CANDIDATES)
    sector_col   = find_column(df, SECTOR_COL_CANDIDATES)

    if not all([turnover_col, region_col, sector_col]):
        return RiskError(f"필요한 컬럼을 찾을 수 없습니다. 컬럼 목록: {df.columns.tolist()}")

    # 지역 + 업종 조회 (전국 폴백)
    row = df[(df[region_col] == region) & (df[sector_col] == sector)]
    display_region = region

    if row.empty:
        row = df[(df[region_col] == "전국") & (df[sector_col] == sector)]
        if row.empty:
            return RiskError(f"'{region} / {sector}' 데이터가 없습니다.")
        display_region = f"{region}(→전국 평균 사용)"

    industry_turnover = _resolve_industry_turnover(row[turnover_col].values[0])
    if industry_turnover == 0:
        return RiskError("업계 중앙값 회전율이 0입니다.")

    my_turnover = my_sales / my_ar_amount
    ratio       = my_turnover / industry_turnover
    risk_key    = _classify_risk(ratio)
    level_info  = RISK_LEVELS[risk_key]

    gauge = (
        min(ratio * 50, 100)          # very_good: 비율에 비례
        if risk_key == "very_good"
        else level_info["gauge"]
    )

    return RiskResult(
        region=display_region,
        sector=sector,
        my_turnover=my_turnover,
        industry_turnover=industry_turnover,
        ratio=ratio,
        my_days=365 / my_turnover,
        industry_days=365 / industry_turnover,
        risk_key=risk_key,
        label=level_info["label"],
        color=level_info["color"],
        emoji=level_info["emoji"],
        gauge_value=gauge,
        advice=level_info["advice"],
        st_func=level_info["st_func"],
    )
