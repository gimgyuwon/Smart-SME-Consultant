"""
src/domain/recommend.py
"""
from __future__ import annotations

import re
from collections import Counter

import pandas as pd
import streamlit as st

from src.config import (
    LDA_MIN_DOCS,
    LDA_NUM_TOPICS,
    LDA_PASSES,
    LDA_RANDOM_STATE,
    NLP_CLEAN_PATTERN,
    NLP_STOPWORDS,
)

# ── NLP 라이브러리 선택적 임포트 ─────────────────────
try:
    from konlpy.tag import Okt
    from gensim import corpora
    from gensim.models import LdaModel
    NLP_AVAILABLE = True
except ImportError:
    NLP_AVAILABLE = False


# ── 공개 API ──────────────────────────────────────────

def is_nlp_available() -> bool:
    """KoNLPy + Gensim 사용 가능 여부를 반환합니다."""
    return NLP_AVAILABLE


def tokenize(titles: list[str]) -> list[list[str]]:
    """
    공고 제목 목록에서 토큰(명사)을 추출합니다.

    KoNLPy 사용 가능 시: 형태소 분석으로 명사 추출
    KoNLPy 미설치 시: 공백 기준 단순 분리 (폴백)

    Args:
        titles: 공고 제목 목록

    Returns:
        토큰화된 문서 목록
    """
    if NLP_AVAILABLE:
        return _tokenize_with_okt(titles)
    return _tokenize_fallback(titles)


def get_top_keywords(titles: list[str], n: int = 10) -> list[tuple[str, int]]:
    """
    공고 제목에서 상위 n개 키워드와 빈도를 반환합니다.

    Args:
        titles: 공고 제목 목록
        n:      반환할 키워드 수

    Returns:
        [(키워드, 빈도)] 리스트
    """
    tokenized = tokenize(titles)
    all_words  = [w for doc in tokenized for w in doc]
    return Counter(all_words).most_common(n)


@st.cache_resource(show_spinner=False)
def build_lda_model(
    titles_tuple: tuple[str, ...],
    num_topics: int = LDA_NUM_TOPICS,
) -> tuple:
    """
    LDA 모델을 학습하고 (model, dictionary, corpus, tokenized) 를 반환합니다.

    st.cache_resource로 캐싱되어 동일한 titles_tuple에 대해 재학습하지 않습니다.
    tuple 타입은 hashable이므로 캐시 키로 사용 가능합니다.

    Args:
        titles_tuple: 공고 제목 튜플 (캐시 키)
        num_topics:   토픽 수

    Returns:
        (LdaModel | None, Dictionary | None, corpus | None, tokenized_docs)
    """
    if not NLP_AVAILABLE:
        return None, None, None, []

    tokenized = [d for d in tokenize(list(titles_tuple)) if d]

    if len(tokenized) < LDA_MIN_DOCS:
        return None, None, None, tokenized

    dictionary = corpora.Dictionary(tokenized)
    corpus     = [dictionary.doc2bow(doc) for doc in tokenized]

    if not corpus:
        return None, None, None, tokenized

    model = LdaModel(
        corpus,
        num_topics=num_topics,
        id2word=dictionary,
        passes=LDA_PASSES,
        random_state=LDA_RANDOM_STATE,
    )
    return model, dictionary, corpus, tokenized


def assign_dominant_topics(model, corpus: list, n_docs: int) -> list[int]:
    """
    각 문서의 주 토픽 ID를 리스트로 반환합니다.

    Args:
        model:  학습된 LdaModel
        corpus: BoW 코퍼스
        n_docs: 원본 DataFrame의 문서 수 (corpus와 길이가 다를 수 있음)

    Returns:
        주 토픽 ID 목록 (길이: n_docs)
    """
    topics = [_dominant_topic(model, bow) for bow in corpus]
    # corpus가 짧을 경우 0으로 채움
    topics += [0] * max(0, n_docs - len(topics))
    return topics[:n_docs]


def recommend_by_query(
    query: str,
    notices_df: pd.DataFrame,
    model,
    dictionary,
    num: int = 5,
) -> pd.DataFrame:
    """
    사용자 쿼리와 가장 유사한 토픽의 공고를 최신순으로 반환합니다.

    LDA 모델이 없으면 전체 목록의 상위 num개를 반환합니다.

    Args:
        query:       사용자 입력 텍스트
        notices_df:  공고 DataFrame (Dominant_Topic 컬럼 포함)
        model:       학습된 LdaModel (None이면 폴백)
        dictionary:  학습된 Dictionary (None이면 폴백)
        num:         반환할 공고 수

    Returns:
        추천 공고 DataFrame
    """
    if model is None or dictionary is None:
        return notices_df.head(num)

    cleaned_q   = re.sub(NLP_CLEAN_PATTERN, " ", query).strip()
    query_tokens = _extract_tokens(cleaned_q)

    if not query_tokens:
        return notices_df.head(num)

    q_bow    = dictionary.doc2bow(query_tokens)
    q_topics = model.get_document_topics(q_bow)

    if not q_topics:
        return notices_df.head(num)

    dominant_id = max(q_topics, key=lambda x: x[1])[0]
    return notices_df[notices_df["Dominant_Topic"] == dominant_id].head(num)


# ── 내부 헬퍼 ──────────────────────────────────────

def _clean_title(title: str) -> str:
    return re.sub(NLP_CLEAN_PATTERN, " ", title).strip()


def _filter_tokens(words: list[str]) -> list[str]:
    return [w for w in words if len(w) > 1 and w not in NLP_STOPWORDS]


def _extract_tokens(text: str) -> list[str]:
    """단일 텍스트에서 토큰을 추출합니다 (NLP 가용 여부에 따라 분기)."""
    if NLP_AVAILABLE:
        okt = Okt()
        return _filter_tokens(okt.nouns(text))
    return _filter_tokens(text.split())


def _tokenize_with_okt(titles: list[str]) -> list[list[str]]:
    okt = Okt()
    return [_filter_tokens(okt.nouns(_clean_title(t))) for t in titles]


def _tokenize_fallback(titles: list[str]) -> list[list[str]]:
    return [_filter_tokens(_clean_title(t).split()) for t in titles]


def _dominant_topic(model, bow) -> int:
    topics = model.get_document_topics(bow)
    return max(topics, key=lambda x: x[1])[0] if topics else 0
