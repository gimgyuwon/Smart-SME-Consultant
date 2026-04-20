import re
import requests
import json
import pandas as pd
import plotly.graph_objects as go
import streamlit as st

try:
    from konlpy.tag import Okt
    from gensim import corpora
    from gensim.models import LdaModel
    NLP_AVAILABLE = True
except ImportError:
    NLP_AVAILABLE = False

# ──────────────────────────────────────────────
# 상수
# ──────────────────────────────────────────────
SEMAS_URL = "https://ols.semas.or.kr/ols/man/SMAN051M/search.do"

STOPWORDS = [
    "신청", "안내", "게시", "자금", "자료", "이수", "교육", "수정",
    "대출", "특별", "직접", "대리", "만기", "연장", "상환", "유예",
    "접수", "소상", "공인", "정책", "지원", "사업",
]
CLEAN_PATTERN = r"\[.*?\]|\(.*?\)|[\s\.\,\:\-\'\"\`\<\>\|\=\+]+|(\d{4}년)|(\d{1,2}월)|(\d{1,2}분기)|(\d{1,2}회)|안내자료"

# ──────────────────────────────────────────────
# SEMAS 공고 수집
# ──────────────────────────────────────────────
@st.cache_data(ttl=3600, show_spinner=False)
def fetch_semas_notices(pages: int = 3) -> pd.DataFrame:
    """SEMAS POST API에서 공고 목록을 수집합니다."""
    all_notices = []
    for page_num in range(1, pages + 1):
        payload = {"bltwtrTitNm": "", "pageNo": str(page_num), "searchStd": "1"}
        try:
            response = requests.post(SEMAS_URL, data=payload, timeout=10)
            response.raise_for_status()
            data = response.json()
            notice_list = data.get("result", [])
            all_notices.extend(notice_list)
        except Exception as e:
            st.warning(f"{page_num}페이지 수집 실패: {e}")
            break

    if not all_notices:
        return pd.DataFrame()

    df = pd.DataFrame(all_notices)
    cols_map = {
        "rnum":         "번호",
        "loanSeCdNm":   "대출구분",
        "bltwtrClcd":   "구분",
        "bltwtrTitNm":  "제목",
        "frstRegDt":    "등록일",
    }
    existing = {k: v for k, v in cols_map.items() if k in df.columns}
    return df[list(existing.keys())].rename(columns=existing)


# ──────────────────────────────────────────────
# 샘플 공고 (API 불가 시 폴백)
# ──────────────────────────────────────────────
SAMPLE_NOTICES = [
    {"번호": 1,  "대출구분": "경영안정자금", "제목": "소상공인 경영위기 긴급경영안정자금 신청 안내",           "등록일": "2026-04-15"},
    {"번호": 2,  "대출구분": "성장촉진자금", "제목": "2026년 소상공인 스마트공방 기술보급사업 공고",          "등록일": "2026-04-12"},
    {"번호": 3,  "대출구분": "경영안정자금", "제목": "전통시장 화재공제 지원 사업 안내",                       "등록일": "2026-04-10"},
    {"번호": 4,  "대출구분": "창업지원자금", "제목": "청년 창업사관학교 신규 입교생 모집 공고",               "등록일": "2026-04-08"},
    {"번호": 5,  "대출구분": "성장촉진자금", "제목": "소상공인 디지털 전환 지원 사업 참여기업 모집",          "등록일": "2026-04-06"},
    {"번호": 6,  "대출구분": "경영안정자금", "제목": "2026년 소상공인 협동조합 활성화 지원 공모",            "등록일": "2026-04-03"},
    {"번호": 7,  "대출구분": "재기지원자금", "제목": "폐업 소상공인 재기 지원 프로그램 신청 접수",            "등록일": "2026-04-01"},
    {"번호": 8,  "대출구분": "경영안정자금", "제목": "소상공인 임차료 부담완화 지원 특별자금 지원",            "등록일": "2026-03-28"},
    {"번호": 9,  "대출구분": "성장촉진자금", "제목": "지역 특화산업 육성 소상공인 역량강화 교육 모집",        "등록일": "2026-03-25"},
    {"번호": 10, "대출구분": "창업지원자금", "제목": "여성 소상공인 창업 및 경영 개선 지원사업 공모",         "등록일": "2026-03-22"},
    {"번호": 11, "대출구분": "경영안정자금", "제목": "소상공인 금리부담 완화를 위한 저금리 대환대출 공고",    "등록일": "2026-03-20"},
    {"번호": 12, "대출구분": "성장촉진자금", "제목": "수출 소상공인 글로벌 진출 지원 프로그램 모집",          "등록일": "2026-03-17"},
    {"번호": 13, "대출구분": "경영안정자금", "제목": "재난·재해 피해 소상공인 긴급 생계안정자금 지원",        "등록일": "2026-03-14"},
    {"번호": 14, "대출구분": "성장촉진자금", "제목": "소공인 특화단지 조성 참여업체 모집 공고",               "등록일": "2026-03-12"},
    {"번호": 15, "대출구분": "재기지원자금", "제목": "채무조정 완료 소상공인 재도전 창업 지원사업 공모",      "등록일": "2026-03-10"},
]


# ──────────────────────────────────────────────
# NLP 파이프라인
# ──────────────────────────────────────────────
def _tokenize(titles: list) -> list[list[str]]:
    """제목 목록에서 명사를 추출합니다 (konlpy 없으면 단어 분리 사용)."""
    docs = []
    if NLP_AVAILABLE:
        okt = Okt()
        for title in titles:
            cleaned = re.sub(CLEAN_PATTERN, " ", title).strip()
            nouns = [w for w in okt.nouns(cleaned) if w not in STOPWORDS and len(w) > 1]
            docs.append(nouns)
    else:
        # 폴백: 2글자 이상 어절 분리
        for title in titles:
            cleaned = re.sub(CLEAN_PATTERN, " ", title).strip()
            words = [w for w in cleaned.split() if len(w) > 1 and w not in STOPWORDS]
            docs.append(words)
    return docs


@st.cache_resource(show_spinner=False)
def build_lda_model(titles_tuple: tuple, num_topics: int = 3):
    """LDA 모델을 학습합니다 (캐시)."""
    titles = list(titles_tuple)
    tokenized = _tokenize(titles)
    tokenized = [d for d in tokenized if d]  # 빈 문서 제거

    if len(tokenized) < 3:
        return None, None, None, tokenized

    dictionary = corpora.Dictionary(tokenized)
    corpus = [dictionary.doc2bow(doc) for doc in tokenized]

    if not corpus:
        return None, None, None, tokenized

    model = LdaModel(corpus, num_topics=num_topics, id2word=dictionary, passes=15, random_state=42)
    return model, dictionary, corpus, tokenized


def _dominant_topic(lda_model, bow) -> int:
    topics = lda_model.get_document_topics(bow)
    return max(topics, key=lambda x: x[1])[0] if topics else 0


def recommend(query: str, df: pd.DataFrame, lda_model, dictionary, num: int = 5) -> pd.DataFrame:
    """쿼리와 가장 유사한 토픽의 공고를 최신순으로 반환합니다."""
    cleaned_q = re.sub(CLEAN_PATTERN, " ", query).strip()
    if NLP_AVAILABLE:
        okt = Okt()
        query_nouns = [w for w in okt.nouns(cleaned_q) if w not in STOPWORDS and len(w) > 1]
    else:
        query_nouns = [w for w in cleaned_q.split() if len(w) > 1 and w not in STOPWORDS]

    if not query_nouns:
        return df.head(num)

    q_bow = dictionary.doc2bow(query_nouns)
    q_topics = lda_model.get_document_topics(q_bow)
    if not q_topics:
        return df.head(num)

    dominant_id = max(q_topics, key=lambda x: x[1])[0]
    return df[df["Dominant_Topic"] == dominant_id].head(num)


# ──────────────────────────────────────────────
# Streamlit 렌더링
# ──────────────────────────────────────────────
def render_recommend_tab():
    st.markdown("## 🏦 정책자금 맞춤 추천")
    st.markdown(
        "소상공인시장진흥공단(SEMAS) 공고를 수집해 **LDA 토픽 모델링**으로 분류한 후, "
        "내 상황과 가장 관련 높은 정책자금을 추천합니다."
    )

    if not NLP_AVAILABLE:
        st.info("💡 `konlpy` 또는 `gensim`이 설치되지 않아 키워드 기반 간단 매칭 모드로 동작합니다.")

    # ── 데이터 수집 ──────────────────────────────
    col_l, col_r = st.columns([3, 1])
    with col_l:
        use_sample_notices = st.checkbox("📂 샘플 공고 사용 (API 미접속)", value=False)
    with col_r:
        pages = st.number_input("수집 페이지 수", min_value=1, max_value=10, value=3, step=1)

    if use_sample_notices:
        notices_df = pd.DataFrame(SAMPLE_NOTICES)
        st.info("📌 샘플 공고 데이터를 사용 중입니다.")
    else:
        with st.spinner("🌐 SEMAS 공고 수집 중..."):
            notices_df = fetch_semas_notices(pages=int(pages))
        if notices_df.empty:
            st.warning("공고 수집에 실패했습니다. 샘플 데이터를 사용합니다.")
            notices_df = pd.DataFrame(SAMPLE_NOTICES)

    st.caption(f"📄 총 {len(notices_df)}개 공고 수집 완료")

    # ── 키워드 빈도 차트 ──────────────────────────
    titles = notices_df["제목"].tolist()
    tokenized = _tokenize(titles)
    all_words = [w for doc in tokenized for w in doc]

    if all_words:
        from collections import Counter
        word_counts = Counter(all_words)
        top10 = word_counts.most_common(10)

        st.markdown("#### 📊 정책 공고 TOP 10 키워드")
        words, counts = zip(*top10)
        fig_kw = go.Figure(go.Bar(
            x=counts[::-1],
            y=words[::-1],
            orientation="h",
            marker=dict(
                color=counts[::-1],
                colorscale="Blues",
                showscale=False,
            ),
            text=counts[::-1],
            textposition="outside",
        ))
        fig_kw.update_layout(
            height=340,
            paper_bgcolor="rgba(0,0,0,0)",
            plot_bgcolor="rgba(0,0,0,0)",
            xaxis=dict(showgrid=False),
            yaxis=dict(showgrid=False),
            margin=dict(t=10, b=10, l=10, r=10),
            font=dict(color="white"),
        )
        st.plotly_chart(fig_kw, use_container_width=True)

    st.divider()

    # ── LDA 학습 ────────────────────────────────
    with st.spinner("🧠 LDA 토픽 모델 학습 중..."):
        lda_model, dictionary, corpus, tokenized_docs = build_lda_model(
            tuple(titles), num_topics=3
        )

    # 도미넌트 토픽 할당
    if lda_model and dictionary and corpus:
        dominant_topics = [_dominant_topic(lda_model, bow) for bow in corpus]
        notices_df = notices_df.copy()
        notices_df["Dominant_Topic"] = dominant_topics[:len(notices_df)]
    else:
        notices_df = notices_df.copy()
        notices_df["Dominant_Topic"] = 0

    # ── 사용자 쿼리 입력 ──────────────────────────
    st.markdown("#### 🔍 내 상황 설명 또는 키워드 입력")

    col_q1, col_q2 = st.columns([4, 1])
    query = col_q1.text_area(
        "상황을 자유롭게 입력하세요",
        placeholder="예: 요즘 매출이 안 나와서 자금 운영에 어려움을 겪고 있어요. 긴급 운영자금이 필요합니다.",
        height=80,
    )
    num_rec = col_q2.number_input("추천 수", min_value=1, max_value=10, value=5)

    if st.button("🎯 맞춤 추천받기", use_container_width=True):
        if not query.strip():
            st.warning("상황을 입력해 주세요.")
            return

        if lda_model and dictionary:
            recs = recommend(query, notices_df, lda_model, dictionary, num=int(num_rec))
        else:
            recs = notices_df.head(int(num_rec))

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


def _render_notice_card(row: pd.Series):
    """공고 1건을 카드 형태로 렌더링합니다."""
    loan_type = row.get("대출구분", "")
    title = row.get("제목", "")
    date = row.get("등록일", "")

    type_colors = {
        "경영안정자금": "#FF6B6B",
        "성장촉진자금": "#4B9EFF",
        "창업지원자금": "#00C896",
        "재기지원자금": "#FFB347",
    }
    badge_color = type_colors.get(str(loan_type), "#888")

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
