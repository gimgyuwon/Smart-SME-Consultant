# 🛡️ 소상공인 흑자도산 방지 대시보드

> **Official Service**: [http://smecheck.cloud](http://smecheck.cloud)  
> **AI 기반 현금흐름 진단 솔루션** — 데이터 기반의 흑자도산 리스크 관리 및 정책자금 최적 매칭 대시보드입니다.

---

## 📋 목차
1. [서비스 개요](#1-서비스-개요)
2. [주요 기능](#2-주요-기능)
3. [기술 스택 및 아키텍처](#3-기술-스택-및-아키텍처)
4. [로컬 실행 방법](#4-로컬-실행-방법)
5. [Docker 실행 방법](#5-docker-실행-방법)
6. [AWS 배포 가이드 (EC2 + Docker)](#6-aws-배포-가이드-ec2--docker)
7. [HTTPS 및 도메인 설정](#7-https-및-도메인-설정)
8. [데이터 가이드](#8-데이터-가이드)
9. [업데이트 및 유지보수](#9-업데이트-및-유지보수)

---

## 1. 서비스 개요
**흑자도산**이란 장부상 이익은 발생하지만, 매출채권(외상값) 회수가 늦어져 실제 현금이 바닥나 임금이나 임대료를 지불하지 못해 망하는 현상입니다.  
본 서비스는 소상공인들이 자신의 현금흐름을 객관적으로 파악하고, 위기 시 활용 가능한 정책자금을 AI 기반으로 추천받을 수 있도록 돕습니다.

---

## 2. 주요 기능

### 💰 탭 1 — 현금흐름 예측 (Cashflow Forecast)
- **AI 예측**: Meta의 **Prophet** 라이브러리를 사용하여 과거 매출/매입 데이터를 학습하고 미래 현금흐름을 예측합니다.
- **위기 알림**: 이번 달 말까지의 예상 잔고를 시뮬레이션하여 현금 부족이 예상되는 날짜와 금액을 경고합니다.
- **시각화**: 누적 순현금, 예측 신뢰구간(90%), 대출 상환 일정(스택 바 차트)을 제공합니다.

### 🚨 탭 2 — 흑자도산 위험도 진단 (Risk Diagnosis)
- **업계 벤치마킹**: 소상공인시장진흥공단의 통계 데이터를 활용하여 내 사업장의 **매출채권 회전율**을 업계 평균과 비교합니다.
- **위험 지수**: 업계 대비 회수 속도를 게이지 차트로 시각화하고 4단계(매우양호/보통/주의/위험) 등급을 부여합니다.
- **회수기간 비교**: 내 사업과 업계 중앙값의 평균 회수일수(Days) 차이를 분석합니다.

### 🏦 탭 3 — 정책자금 맞춤 추천 (Funding Recommendation)
- **실시간 데이터**: **SEMAS API**를 통해 최신 정책자금 공고를 실시간으로 수집합니다.
- **토픽 모델링**: **Gensim LDA** 모델을 사용하여 수천 개의 공고를 주제별로 분류합니다.
- **상황 기반 추천**: 사용자가 현재 겪고 있는 어려움을 텍스트로 입력하면, AI가 가장 관련성 높은 공고를 최신순으로 추천합니다.

---

## 3. 기술 스택 및 아키텍처

### 핵심 기술
- **Frontend/UI**: Streamlit (Modern Dark Theme)
- **AI/ML**: Meta Prophet (시계열 예측), Gensim (LDA 토픽 모델링), KoNLPy (한글 형태소 분석)
- **Data**: Pandas, NumPy
- **Visuals**: Plotly Interactive Charts
- **Server**: Nginx (Reverse Proxy), Docker & Docker Compose

### 🏗️ 3계층 클린 아키텍처 (src/)
본 프로젝트는 유지보수성을 극대화하기 위해 코드를 3개의 계층으로 분리하였습니다.
```
src/
├── config.py           # 모든 상수, 경로, 설정값 한 곳에서 관리
├── data/               # [Data Layer] 파일 I/O 및 API 호출 (Requests)
├── domain/             # [Domain Layer] 순수 비즈니스 로직 및 AI 모델링 (Streamlit 의존성 없음)
└── ui/                 # [UI Layer] Streamlit 컴포넌트 및 스타일 (Plotly 렌더링)
```

---

## 4. 로컬 실행 방법

### 1단계: 환경 준비 (Java 필수)
**KoNLPy** 사용을 위해 JDK 8 이상의 설치가 필요합니다.
- [JDK 설치 가이드](https://www.oracle.com/java/technologies/downloads/)
- `JAVA_HOME` 환경변수를 설정해야 합니다.

### 2단계: 의존성 설치
```bash
git clone https://github.com/<your-username>/data_anal.git
cd data_anal
pip install -r requirements.txt
```

### 3단계: 실행
```bash
streamlit run app.py
```

---

## 5. Docker 실행 방법

별도의 Python 설치 없이 컨테이너 환경에서 즉시 실행 가능합니다. (Java 환경 내장)

### 로컬 테스트
```bash
docker compose up --build
```
- 접속 주소: `http://localhost:8501`

---

## 6. AWS 배포 가이드 (EC2 + Docker)

### 1단계: EC2 인스턴스 사양 추천
- **추천**: t3.small (2 vCPU, 2GB RAM)
- **최소**: t3.micro (메모리 부족으로 모델 학습이 끊길 수 있음)
- **볼륨**: gp3 20GB 이상 추천
- **보안그룹 규칙**: 22(SSH), 80(HTTP), 443(HTTPS) 인바운드 허용

### 2단계: EC2 초기 설정 (자동화)
SSH 접속 후 아래 명령어를 실행하면 Docker 및 필수 패키지가 자동 설치됩니다.
```bash
git clone https://github.com/<your-username>/data_anal.git
cd data_anal
chmod +x deploy/setup-ec2.sh
sudo ./deploy/setup-ec2.sh
```

### 3단계: 프로덕션 모드 배포
Nginx와 함께 배포하여 대외 서비스를 안정적으로 제공합니다.
```bash
# 로그아웃 후 다시 접속 (docker 그룹 권한 적용)
docker compose -f docker-compose.prod.yml up -d --build
```

---

## 7. HTTPS 및 도메인 설정

도메인을 EC2 IP에 연결한 상태에서만 가능합니다.

### HTTPS 자동 비활성
```bash
chmod +x deploy/https-setup.sh
sudo ./deploy/https-setup.sh your-domain.com your@email.com
```
이 스크립트는 **Let's Encrypt** 인증서를 발급하고 Nginx 설정을 자동으로 업데이트합니다.

---

## 8. 데이터 가이드

### `data/sme_data.csv`
- 소상공인시장진흥공단에서 제공하는 통계 데이터.
- 인코딩: `UTF-16`, 구분자: `TAB`.
- 업종별/지역별 매출채권 회전율 중앙값을 포함합니다.

### `data/sample_codef_data.json`
- 탭 1 시연을 위한 가상 데이터.
- `invoices`와 `loans` 키를 가진 JSON 형식으로, 실제 데이터를 업로드하여 분석할 수 있습니다.

---

## 9. 업데이트 및 유지보수

코드를 수정하고 GitHub에 푸시한 뒤, 서버에서 한 줄로 업데이트 가능합니다.
```bash
# EC2에서 실행
cd ~/data_anal && git pull && docker compose -f docker-compose.prod.yml up -d --build && docker system prune -f
```

---

## 👨‍💻 기여 및 문의
- 본 프로젝트는 소상공인들의 안정적인 사업 운영 지원을 목표로 합니다.
- 버그 제보 및 기능 제안은 Issue 탭을 이용해 주세요.

---

> **면책 조항**: 본 대시보드에서 제공하는 예측 데이터와 위험도는 통계와 AI 알고리즘에 기반한 참고 수치일 뿐이며, 법적 효력이 없습니다. 실제 경영 판단 시에는 세무/회계 전문가와 상의하시기 바랍니다.
