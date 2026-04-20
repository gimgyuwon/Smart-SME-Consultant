"""
src/data/semas_api.py
"""
from __future__ import annotations

import pandas as pd
import requests
import streamlit as st

from src.config import (
    SEMAS_CACHE_TTL,
    SEMAS_TIMEOUT,
    SEMAS_URL,
)

# API 응답 → 한국어 컬럼명 매핑
_COLUMN_MAP: dict[str, str] = {
    "rnum":        "번호",
    "loanSeCdNm":  "대출구분",
    "bltwtrClcd":  "구분",
    "bltwtrTitNm": "제목",
    "frstRegDt":   "등록일",
}


@st.cache_data(ttl=SEMAS_CACHE_TTL, show_spinner=False)
def fetch_notices(pages: int = 3) -> pd.DataFrame:
    """
    SEMAS POST API에서 정책자금 공고 목록을 수집합니다.

    Args:
        pages: 수집할 페이지 수

    Returns:
        공고 DataFrame. 수집 실패 시 빈 DataFrame.
    """
    all_notices: list[dict] = []

    for page_num in range(1, pages + 1):
        payload = {
            "bltwtrTitNm": "",
            "pageNo":      str(page_num),
            "searchStd":   "1",
        }
        try:
            response = requests.post(SEMAS_URL, data=payload, timeout=SEMAS_TIMEOUT)
            response.raise_for_status()
            notice_list = response.json().get("result", [])
            all_notices.extend(notice_list)
        except requests.exceptions.RequestException as e:
            # 네트워크 오류 → 수집 중단
            raise ConnectionError(f"{page_num}페이지 요청 실패: {e}") from e

    if not all_notices:
        return pd.DataFrame()

    df = pd.DataFrame(all_notices)
    existing = {k: v for k, v in _COLUMN_MAP.items() if k in df.columns}
    return df[list(existing.keys())].rename(columns=existing)
