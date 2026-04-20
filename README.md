# 🛡️ 소상공인 흑자도산 방지 대시보드

> **흑자도산(Black Bankruptcy)** — 매출·이익은 발생하지만, 매출채권 회수가 늦어 실제 현금이 부족해 도산하는 현상.  
> 이 프로젝트는 소상공인이 **현금흐름 위기를 미리 감지하고**, 맞춤 정책자금을 추천받을 수 있도록 돕는 Streamlit 기반 대시보드입니다.

<br>

## 📌 주요 기능

| 탭 | 기능 | 핵심 기술 |
|:---:|---|---|
| 💰 **탭 1** | Prophet AI 기반 이번 달 말 현금 부족일 예측 | `prophet`, `plotly` |
| 🚨 **탭 2** | 업종·지역별 매출채권 회전율 비교 흑자도산 위험도 진단 | `pandas`, `plotly` |
| 🏦 **탭 3** | SEMAS 실시간 공고 수집 + LDA 토픽 매칭 정책자금 추천 | `konlpy`, `gensim` |

<br>

## 🖼️ 스크린샷

> `streamlit run app.py` 실행 후 브라우저에서 확인하세요.

<br>

## 🗂️ 프로젝트 구조

```
data_anal/
├── app.py                      # 진입점 — 페이지 설정, 탭 마운트만 담당 (50줄)
├── requirements.txt
├── data/
│   ├── sme_data.csv            # 업종별 매출채권 회전율 통계 (UTF-16, 탭 구분)
│   └── sample_codef_data.json  # 샘플 거래 데이터 (2025.01 ~ 2026.04)
├── src/                        # 핵심 소스 코드 (3계층 아키텍처)
│   ├── config.py               # 전역 상수·경로·설정값 단일 관리
│   ├── data/                   # 📦 데이터 접근 계층 (I/O만 담당)
│   │   ├── loaders.py          #   JSON / CSV 파일 로드
│   │   └── semas_api.py        #   SEMAS POST API 호출
│   ├── domain/                 # 🔬 비즈니스 로직 계층 (Streamlit 의존성 없음)
│   │   ├── cashflow.py         #   현금흐름 계산 + Prophet 예측
│   │   ├── risk.py             #   매출채권 회전율 위험도 계산
│   │   └── recommend.py        #   NLP 전처리 + LDA 토픽 모델링
│   └── ui/                     # 🎨 UI 계층 (Streamlit 렌더링만 담당)
│       ├── styles.py           #   글로벌 다크 테마 CSS
│       ├── sidebar.py          #   사이드바 컴포넌트
│       ├── cashflow_tab.py     #   탭1 UI
│       ├── risk_tab.py         #   탭2 UI
│       └── recommend_tab.py    #   탭3 UI
└── docs/
    └── guide.md                # 프로젝트 가이드 문서
```

<br>

## ⚙️ 아키텍처 설계 원칙

본 프로젝트는 **관심사의 분리(Separation of Concerns)** 를 기반으로 3계층 구조로 설계되었습니다.

```
┌───────────────────────────────────┐
│          UI Layer (src/ui/)       │  ← Streamlit 렌더링만
├───────────────────────────────────┤
│      Domain Layer (src/domain/)   │  ← 순수 Python 비즈니스 로직
├───────────────────────────────────┤
│       Data Layer (src/data/)      │  ← 파일 I/O / API 통신만
└───────────────────────────────────┘
         ↑ 모든 상수는 src/config.py에서 관리
```

- **Domain 계층은 Streamlit에 전혀 의존하지 않아** 독립적으로 테스트 가능합니다.
- 비즈니스 로직 결과는 `RiskResult`, `CashflowForecastResult` **데이터클래스**로 타입 안전하게 반환됩니다.
- API 오류는 `ConnectionError`로 표준화되어 UI 계층에서 일관되게 처리합니다.

<br>

## 🚀 빠른 시작

### 1. 저장소 클론

```bash
git clone https://github.com/<your-username>/data_anal.git
cd data_anal
```

### 2. 가상 환경 생성 (권장)

```bash
python -m venv .venv

# Windows
.venv\Scripts\activate

# macOS / Linux
source .venv/bin/activate
```

### 3. 의존성 설치

```bash
pip install -r requirements.txt
```

> **⚠️ KoNLPy (Windows) 주의사항**  
> KoNLPy는 JVM(Java) 기반입니다. 설치 전 **JDK 8 이상**이 필요합니다.  
> - [JDK 다운로드](https://www.oracle.com/java/technologies/downloads/)  
> - `JAVA_HOME` 환경변수 설정 필요  
> - KoNLPy 미설치 시 탭3는 **단어 분리 기반 폴백 모드**로 동작합니다.

### 4. 앱 실행

```bash
streamlit run app.py
```

브라우저에서 `http://localhost:8501` 접속

<br>

## 📊 데이터 가이드

### `data/sme_data.csv`

소상공인시장진흥공단 제공 업종별 매출채권 회전율 통계 데이터입니다.

| 컬럼 | 설명 |
|---|---|
| 시도명 | 지역 (예: 서울, 경기, 전국) |
| 업종 대분류 | 업종 분류 (예: 도매 및 소매업) |
| 중앙값 매출채권회전율 | 해당 업종·지역의 중앙값 회전율 |

- 인코딩: `UTF-16 (BOM 포함)`, 구분자: `탭(\t)`
- 총 433개 행

### `data/sample_codef_data.json`

탭1 현금흐름 예측용 샘플 데이터입니다. 실제 데이터 구조는 아래와 같습니다.

```json
{
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
}
```

> 실제 거래 데이터를 넣으면 탭1의 **파일 업로드** 기능으로 분석할 수 있습니다.

<br>

## 🔬 탭별 상세 기능

### 💰 탭 1 — 현금흐름 예측

1. 거래 JSON 파일 업로드 (또는 샘플 데이터 사용)  
2. **Prophet** 모델이 일별 순현금흐름(매출 − 매입 − 대출상환)을 학습  
3. 이번 달 말까지 예측 — 잔고 < 0이 되는 날짜 감지  
4. 시각화 3종: **누적 실제현금**, **Prophet 예측(90% 신뢰구간)**, **종류별 대출 예정**

### 🚨 탭 2 — 흑자도산 위험도 진단

1. 지역·업종·연매출·매출채권 잔액을 입력  
2. `중앙값 매출채권회전율 = 연매출 ÷ 매출채권잔액` 계산  
3. 업계 중앙값 대비 비율로 **4단계 등급** 부여

| 등급 | 기준 | 의미 |
|:---:|:---:|---|
| 🟢 매우 양호 | 비율 ≥ 1.2 | 회전율이 업계 대비 높음 |
| 🟡 보통 | 0.8 ~ 1.2 | 업계 평균 수준 |
| 🟠 주의 | 0.5 ~ 0.8 | 회수 속도 느림 |
| 🔴 위험 | < 0.5 | 현금흐름 악화 위험 |

> 해당 지역·업종 데이터가 없으면 **전국 평균**으로 자동 폴백됩니다.

### 🏦 탭 3 — 정책자금 맞춤 추천

1. SEMAS API에서 최신 공고 수집 (1시간 캐싱)  
2. `KoNLPy(Okt)`로 명사 추출 → `gensim LDA`로 3개 토픽 분류  
3. 사용자 상황 입력 → 토픽 매칭 → 최신순 추천  
4. 샘플 공고 15건 내장 (API 미접속 환경 지원)

<br>

## 🛠️ 기술 스택

| 분류 | 라이브러리 | 용도 |
|:---:|---|---|
| **웹 프레임워크** | `streamlit >= 1.32` | 대시보드 UI |
| **데이터 처리** | `pandas >= 2.0`, `numpy >= 1.26` | 데이터 전처리 |
| **예측 모델** | `prophet >= 1.1.5` | 시계열 현금흐름 예측 |
| **시각화** | `plotly >= 5.20` | 인터랙티브 차트 |
| **NLP** | `konlpy >= 0.6`, `gensim >= 4.3` | 형태소 분석 + LDA |
| **API 통신** | `requests >= 2.31` | SEMAS HTTP 크롤링 |

<br>

## 🤝 기여 방법

```bash
# 1. 포크 후 브랜치 생성
git checkout -b feature/기능명

# 2. 변경사항 커밋
git commit -m "feat: 기능 설명"

# 3. 푸시
git push origin feature/기능명

# 4. Pull Request 생성
```

### 커밋 컨벤션

| 타입 | 설명 |
|---|---|
| `feat` | 새 기능 추가 |
| `fix` | 버그 수정 |
| `refactor` | 리팩토링 |
| `docs` | 문서 수정 |
| `style` | 코드 스타일 (포맷 등) |
| `test` | 테스트 추가/수정 |
| `chore` | 빌드, 의존성 등 기타 |

<br>

## 📄 라이선스

MIT License — 자유롭게 사용·수정·배포 가능합니다.

<br>

## 🙏 데이터 출처

- **업종별 매출채권 회전율**: [소상공인시장진흥공단(SEMAS)](https://www.semas.or.kr)  
- **정책자금 공고**: [소상공인 온라인 지원시스템](https://ols.semas.or.kr)

<br>

---

> 본 서비스는 참고용이며, 실제 경영 의사결정에는 전문가 상담을 권장합니다.
