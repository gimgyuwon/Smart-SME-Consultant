"""
src/data/loaders.py — 파일 I/O 계층
JSON 및 CSV 데이터 로드를 담당합니다.
비즈니스 로직·UI 코드는 포함하지 않습니다.
"""
from __future__ import annotations

import json
from pathlib import Path
from typing import Union

import pandas as pd
import streamlit as st

from src.config import SME_CSV_ENCODING, SME_CSV_SEP


def load_json(source: Union[str, Path, object]) -> dict:
    """
    파일 경로(str/Path) 또는 파일 객체(st.UploadedFile 등)에서
    JSON 데이터를 로드합니다.

    Args:
        source: 파일 경로 또는 파일 객체

    Returns:
        파싱된 dict
    """
    if isinstance(source, (str, Path)):
        with open(source, "r", encoding="utf-8") as f:
            return json.load(f)
    return json.load(source)


@st.cache_data(show_spinner=False)
def load_sme_data(path: str = "data/sme_data.csv") -> pd.DataFrame:
    """
    업종별 매출채권 회전율 통계 CSV를 로드합니다.

    인코딩: UTF-16 (BOM 포함), 탭 구분자
    핵심 컬럼: 시도명, 업종 대분류, 중앙값 매출채권회전율

    Args:
        path: CSV 파일 경로

    Returns:
        정제된 DataFrame
    """
    df = pd.read_csv(path, encoding=SME_CSV_ENCODING, sep=SME_CSV_SEP)
    df.columns = df.columns.str.strip()

    if "시도명" in df.columns:
        df["시도명"] = df["시도명"].fillna("전국").str.strip()

    return df


def find_column(df: pd.DataFrame, candidates: list[str]) -> str | None:
    """
    DataFrame에서 후보 컬럼명 목록 중 실제 존재하는 첫 번째 컬럼을 반환합니다.

    Args:
        df: 대상 DataFrame
        candidates: 후보 컬럼명 목록 (우선순위 순)

    Returns:
        존재하는 첫 번째 컬럼명. 없으면 None.
    """
    for col in candidates:
        if col in df.columns:
            return col
    return None
