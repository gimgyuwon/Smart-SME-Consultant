"""
src/ui/recommend_tab.py — 탭3 정책자금 추천 UI
도메인 로직은 src.domain.recommend에, API 호출은 src.data.semas_api에 위임합니다.
"""
from __future__ import annotations

import pandas as pd
import plotly.graph_objects as go
import streamlit as st

from src.config import LOAN_TYPE_COLORS, SAMPLE_NOTICES
from src.data.semas_api import fetch_notices
from src.domain.recommend import (
    assign_dominant_topics,
    build_lda_model,
    get_top_keywords,
    is_nlp_available,
    recommend_by_query,
)


def render_recommend_tab() -> None:
    """탭3 전체를 렌더링합니다."""
    st.markdown("## 🏦 정책자금 맞춤 추천")
    st.markdown(
        "소상공인시장진흥공단(SEMAS) 공고를 수집해 **LDA 토픽 모델링**으로 분류한 후, "
        "내 상황과 가장 관련 높은 정책자금을 추천합니다."
    )

    if not is_nlp_available():
        st.info("💡 `konlpy` 또는 `gensim`이 설치되지 않아 키워드 기반 간단 매칭 모드로 동작합니다.")

    notices_df  = _load_notices()
    notices_df  = _attach_topics(notices_df)

    _render_keyword_chart(notices_df["제목"].tolist())
    st.divider()
    _render_recommendation_form(notices_df)


# ── 데이터 로드 ────────────────────────────────────

def _load_notices() -> pd.DataFrame:
    """공고 데이터를 로드합니다 (실시간 API 또는 샘플)."""
    col_l, col_r = st.columns([3, 1])
    use_sample = col_l.checkbox("📂 샘플 공고 사용 (API 미접속)", value=False)
    pages      = col_r.number_input("수집 페이지 수", min_value=1, max_value=10, value=3)

    if use_sample:
        st.info("📌 샘플 공고 데이터를 사용 중입니다.")
        df = pd.DataFrame(SAMPLE_NOTICES)
    else:
        with st.spinner("🌐 SEMAS 공고 수집 중..."):
            try:
                df = fetch_notices(pages=int(pages))
            except ConnectionError as e:
                st.warning(f"공고 수집 실패: {e}\n샘플 데이터를 사용합니다.")
                df = pd.DataFrame(SAMPLE_NOTICES)

        if df.empty:
            st.warning("공고 수집에 실패했습니다. 샘플 데이터를 사용합니다.")
            df = pd.DataFrame(SAMPLE_NOTICES)

    st.caption(f"📄 총 {len(df)}개 공고 수집 완료")
    return df


def _attach_topics(notices_df: pd.DataFrame) -> pd.DataFrame:
    """LDA 모델을 학습해 각 공고에 주 토픽 ID를 부여합니다."""
    titles = notices_df["제목"].tolist()

    with st.spinner("🧠 LDA 토픽 모델 학습 중..."):
        model, dictionary, corpus, _ = build_lda_model(tuple(titles))

    df = notices_df.copy()
    if model and dictionary and corpus:
        df["Dominant_Topic"] = assign_dominant_topics(model, corpus, len(df))
    else:
        df["Dominant_Topic"] = 0

    return df


# ── UI 컴포넌트 ────────────────────────────────────

def _render_keyword_chart(titles: list[str]) -> None:
    """상위 10개 키워드 수평 막대 차트를 렌더링합니다."""
    top_keywords = get_top_keywords(titles, n=10)
    if not top_keywords:
        return

    st.markdown("#### 📊 정책 공고 TOP 10 키워드")
    words, counts = zip(*top_keywords)

    fig = go.Figure(go.Bar(
        x=counts[::-1],
        y=words[::-1],
        orientation="h",
        marker=dict(color=counts[::-1], colorscale="Blues", showscale=False),
        text=counts[::-1],
        textposition="outside",
    ))
    fig.update_layout(
        height=340,
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)",
        xaxis=dict(showgrid=False),
        yaxis=dict(showgrid=False),
        margin=dict(t=10, b=10, l=10, r=10),
        font=dict(color="white"),
    )
    st.plotly_chart(fig, use_container_width=True)


def _render_recommendation_form(notices_df: pd.DataFrame) -> None:
    """사용자 쿼리 입력 폼과 추천 결과를 렌더링합니다."""
    # 쿼리를 session_state에 저장해 rerurn 시 유지
    if "recommend_query" not in st.session_state:
        st.session_state.recommend_query = ""

    st.markdown("#### 🔍 내 상황 설명 또는 키워드 입력")
    col_q1, col_q2 = st.columns([4, 1])
    query   = col_q1.text_area(
        "상황을 자유롭게 입력하세요",
        value=st.session_state.recommend_query,
        placeholder="예: 요즘 매출이 안 나와서 자금 운영에 어려움을 겪고 있어요.",
        height=80,
        key="query_input",
    )
    num_rec = col_q2.number_input("추천 수", min_value=1, max_value=10, value=5)

    if st.button("🎯 맞춤 추천받기", use_container_width=True):
        if not query.strip():
            st.warning("상황을 입력해 주세요.")
            return

        model, dictionary, _, _ = build_lda_model(tuple(notices_df["제목"].tolist()))
        recs = recommend_by_query(query, notices_df, model, dictionary, num=int(num_rec))

        st.markdown(f"#### ✅ 추천 결과 ({len(recs)}건)")
        if recs.empty:
            st.info("조건에 맞는 공고가 없습니다. 더 다양한 키워드를 입력해 보세요.")
        else:
            for _, row in recs.iterrows():
                _render_notice_card(row)
    else:
        st.markdown("#### 📋 전체 공고 목록")
        show_cols = [c for c in ["번호", "대출구분", "제목", "등록일"] if c in notices_df.columns]
        st.dataframe(notices_df[show_cols], use_container_width=True, hide_index=True)


def _render_notice_card(row: pd.Series) -> None:
    """공고 1건을 배지 + 제목 카드 형태로 렌더링합니다."""
    loan_type    = row.get("대출구분", "")
    title        = row.get("제목", "")
    date         = row.get("등록일", "")
    badge_color  = LOAN_TYPE_COLORS.get(str(loan_type), "#888")

    st.markdown(
        f"""
        <div style="
            background: rgba(255,255,255,0.05);
            border: 1px solid rgba(255,255,255,0.1);
            border-radius: 12px;
            padding: 16px 20px;
            margin-bottom: 10px;
        ">
            <span style="
                background: {badge_color};
                color: white;
                padding: 2px 10px;
                border-radius: 20px;
                font-size: 0.78rem;
                font-weight: 600;
            ">{loan_type}</span>
            <span style="
                color: rgba(255,255,255,0.4);
                font-size: 0.78rem;
                margin-left: 10px;
            ">{date}</span>
            <p style="margin: 8px 0 0 0; font-size: 1rem; color: white; font-weight: 500;">{title}</p>
        </div>
        """,
        unsafe_allow_html=True,
    )
