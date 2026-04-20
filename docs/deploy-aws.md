# 🚀 AWS + Docker 배포 가이드

> 이 가이드는 **AWS EC2 + Docker**를 사용해 실제 URL로 접속 가능한 서비스를 구축하는 전 과정을 설명합니다.  
> 예상 비용: 월 **약 $10~20** (t3.small On-Demand, 서울 리전 기준)

---

## 📋 목차

1. [아키텍처 개요](#1-아키텍처-개요)
2. [전제 조건](#2-전제-조건)
3. [AWS EC2 인스턴스 생성](#3-aws-ec2-인스턴스-생성)
4. [보안 그룹 설정](#4-보안-그룹-설정)
5. [EC2 환경 설정](#5-ec2-환경-설정)
6. [앱 배포](#6-앱-배포)
7. [도메인 연결 (선택)](#7-도메인-연결-선택)
8. [HTTPS 설정 (선택)](#8-https-설정-선택)
9. [업데이트 방법](#9-업데이트-방법)
10. [모니터링 & 트러블슈팅](#10-모니터링--트러블슈팅)
11. [비용 최적화 팁](#11-비용-최적화-팁)

---

## 1. 아키텍처 개요

```
인터넷
  │
  ▼
[사용자 브라우저]
  │  HTTP(80) / HTTPS(443)
  ▼
[AWS EC2 인스턴스]
  │
  ├── [Docker: Nginx 컨테이너]  ← 리버스 프록시 + SSL 종단
  │         │  http://streamlit:8501
  │         ▼
  ├── [Docker: Streamlit 컨테이너]  ← 앱 서버
  │
  └── [Docker: Certbot 컨테이너]  ← Let's Encrypt 인증서 자동 갱신
```

**왜 Nginx가 필요한가?**
- Streamlit은 WebSocket을 사용 → Nginx에서 WebSocket 프록시 필수
- 포트 80/443 → 8501 포워딩
- SSL/TLS 종단 처리
- 보안 헤더 추가

---

## 2. 전제 조건

- [ ] AWS 계정 생성 및 로그인
- [ ] 로컬 PC에 SSH 키 파일(`.pem`) 보유
- [ ] (선택) 도메인 구매 — 가비아, 호스팅KR, AWS Route 53 등

---

## 3. AWS EC2 인스턴스 생성

### 콘솔에서 생성

1. **AWS 콘솔** → `EC2` → `인스턴스 시작`

2. **이름 & 태그**  
   ```
   이름: blackbankruptcy-server
   ```

3. **AMI 선택**  
   ```
   Ubuntu Server 22.04 LTS (HVM), SSD Volume Type
   아키텍처: 64비트 (x86)
   ```

4. **인스턴스 유형**

   | 유형 | vCPU | 메모리 | 월 비용(서울) | 추천 |
   |---|:---:|:---:|:---:|:---:|
   | `t3.micro` | 2 | 1 GB | ~$8 | 테스트용 |
   | `t3.small` | 2 | 2 GB | ~$17 | **권장** |
   | `t3.medium` | 2 | 4 GB | ~$33 | 부하 많을 때 |

   > Prophet 모델 학습에 메모리가 필요하므로 **t3.small 이상** 권장

5. **키 페어**  
   - 기존 키 페어 선택 또는 새 키 페어 생성 (`.pem` 다운로드 → 안전한 곳 보관)

6. **네트워크 설정**  
   → 아래 [보안 그룹 설정](#4-보안-그룹-설정) 참고

7. **스토리지**  
   ```
   루트 볼륨: gp3, 20 GB (기본 8GB는 Docker 이미지에 부족)
   ```

8. **인스턴스 시작** 클릭

---

## 4. 보안 그룹 설정

> `EC2` → `보안 그룹` → `인바운드 규칙 편집`

| 규칙 | 유형 | 프로토콜 | 포트 | 소스 | 설명 |
|:---:|---|:---:|:---:|---|---|
| 1 | SSH | TCP | 22 | 내 IP | SSH 접속 |
| 2 | HTTP | TCP | 80 | 0.0.0.0/0 | 웹 접속 |
| 3 | HTTPS | TCP | 443 | 0.0.0.0/0 | HTTPS |

> ⚠️ SSH는 반드시 **내 IP**로만 제한하세요.

---

## 5. EC2 환경 설정

### SSH 접속

```bash
# 권한 설정 (macOS/Linux)
chmod 400 your-key.pem

# 접속
ssh -i your-key.pem ubuntu@<EC2-퍼블릭-IP>
```

> Windows에서는 PuTTY 또는 MobaXterm 또는 Windows Terminal 사용

### 초기 설정 스크립트 실행

```bash
# 저장소 클론 (setup 스크립트 사용)
git clone https://github.com/<your-username>/data_anal.git
cd data_anal

# 설정 스크립트 실행 (Docker 설치 + 방화벽 설정)
chmod +x deploy/setup-ec2.sh
sudo ./deploy/setup-ec2.sh
```

스크립트가 자동으로 처리하는 항목:
- 시스템 패키지 업데이트
- Docker + Docker Compose 설치
- UFW 방화벽 설정 (22, 80, 443 허용)

```bash
# ⚠️ Docker 그룹 권한 적용을 위해 재접속
exit
ssh -i your-key.pem ubuntu@<EC2-퍼블릭-IP>
```

---

## 6. 앱 배포

### 저장소 클론 (이미 안 했다면)

```bash
cd ~
git clone https://github.com/<your-username>/data_anal.git
cd data_anal
```

### Docker 이미지 빌드 & 실행

```bash
# 프로덕션 모드로 실행 (Nginx + Streamlit + Certbot)
docker compose -f docker-compose.prod.yml up -d --build
```

> ⏱️ 첫 빌드는 Java + Python 패키지 설치로 **10~20분** 소요됩니다.

### 실행 확인

```bash
# 컨테이너 상태 확인
docker compose -f docker-compose.prod.yml ps

# 로그 확인
docker compose -f docker-compose.prod.yml logs -f

# 헬스체크 확인
curl http://localhost:8501/_stcore/health
```

### 브라우저 접속

```
http://<EC2-퍼블릭-IP>
```

---

## 7. 도메인 연결 (선택)

### DNS A 레코드 설정

도메인 구매 후 DNS 설정에서:

| 레코드 | 이름 | 값 |
|---|---|---|
| A | `@` (또는 `www`) | EC2 퍼블릭 IP |

> DNS 전파: 최대 48시간 (보통 30분 내)

### 탄력적 IP 할당 (EC2 재시작 시 IP 변경 방지)

```
EC2 → 탄력적 IP → 탄력적 IP 주소 할당 → 인스턴스에 연결
```

> ⚠️ 탄력적 IP는 인스턴스에 연결된 동안 무료입니다.

---

## 8. HTTPS 설정 (선택)

> 도메인이 EC2 IP에 연결된 후 실행하세요.

```bash
chmod +x deploy/https-setup.sh
./deploy/https-setup.sh your-domain.com your@email.com
```

스크립트 실행 후 접속:
```
https://your-domain.com
```

### 수동으로 설정하고 싶다면

```bash
# 1. 인증서 발급
docker compose -f docker-compose.prod.yml run --rm certbot \
    certonly --webroot \
    --webroot-path=/var/www/certbot \
    --email your@email.com \
    --agree-tos --no-eff-email \
    -d your-domain.com

# 2. deploy/nginx.conf에서 HTTPS 블록 주석 해제
#    server_name your-domain.com; 으로 수정

# 3. Nginx 재시작
docker compose -f docker-compose.prod.yml restart nginx
```

---

## 9. 업데이트 방법

코드를 수정하고 GitHub에 푸시한 후 EC2에서:

```bash
cd ~/data_anal

# 최신 코드 Pull
git pull origin main

# 이미지 재빌드 & 재시작 (다운타임 최소화)
docker compose -f docker-compose.prod.yml up -d --build

# 사용하지 않는 이미지 정리
docker system prune -f
```

### 매직 원 라이너

```bash
# 한 줄로 업데이트
cd ~/data_anal && git pull && docker compose -f docker-compose.prod.yml up -d --build && docker system prune -f
```

---

## 10. 모니터링 & 트러블슈팅

### 자주 쓰는 명령어

```bash
# 모든 컨테이너 상태
docker compose -f docker-compose.prod.yml ps

# 실시간 로그 (Ctrl+C로 종료)
docker compose -f docker-compose.prod.yml logs -f

# 특정 서비스 로그
docker compose -f docker-compose.prod.yml logs -f streamlit
docker compose -f docker-compose.prod.yml logs -f nginx

# 컨테이너 내부 접속
docker exec -it blackbankruptcy-app bash

# 서비스 재시작
docker compose -f docker-compose.prod.yml restart streamlit

# 전체 중지
docker compose -f docker-compose.prod.yml down

# 전체 중지 + 볼륨 삭제
docker compose -f docker-compose.prod.yml down -v
```

### 서버 리소스 모니터링

```bash
# CPU / 메모리 사용량
htop

# Docker 컨테이너별 리소스
docker stats

# 디스크 사용량
df -h
docker system df
```

### 흔한 문제 해결

| 증상 | 원인 | 해결 |
|---|---|---|
| 접속 불가 | 보안 그룹 80 포트 닫힘 | AWS 콘솔에서 인바운드 규칙 확인 |
| 502 Bad Gateway | Streamlit 컨테이너 미시작 | `docker logs blackbankruptcy-app` |
| 앱 느림 | 메모리 부족 | EC2를 t3.small 이상으로 업그레이드 |
| 디스크 부족 | Docker 이미지 누적 | `docker system prune -a` |
| KoNLPy 오류 | Java 설정 문제 | `docker exec -it blackbankruptcy-app java -version` |

---

## 11. 비용 최적화 팁

### 야간/주말 자동 중지 (개발/테스트 서버)

```bash
# 크론탭 편집
crontab -e

# 평일 오전 9시 시작, 오후 11시 중지 (UTC 기준 → KST -9시간)
0 0  * * 1-5  /usr/bin/docker compose -f /home/ubuntu/data_anal/docker-compose.prod.yml up -d
0 14 * * 1-5  /usr/bin/docker compose -f /home/ubuntu/data_anal/docker-compose.prod.yml down
```

### Savings Plans (1년 약정)

- On-Demand 대비 최대 **40% 할인**
- `EC2` → `Savings Plans` → `구매`

### 스팟 인스턴스 (최대 90% 저렴, 중단 가능)

- 개발·테스트 환경에 적합
- 프로덕션에는 권장하지 않음

---

## 📊 최종 접속 확인 체크리스트

```
[ ] EC2 인스턴스 Running 상태
[ ] 보안 그룹 80, 443 포트 개방
[ ] docker compose ps → 모든 컨테이너 Up(healthy)
[ ] http://<EC2-IP> 접속 → 대시보드 로딩
[ ] (도메인 있으면) https://your-domain.com 접속
[ ] 탭 1: 샘플 데이터 로드 → Prophet 예측 차트 표시
[ ] 탭 2: 위험도 진단 폼 제출 → 게이지 차트 표시
[ ] 탭 3: 샘플 공고 로드 → 키워드 차트 표시
```

---

> 문제가 발생하면 `docker compose logs` 로그와 함께 이슈를 등록해 주세요.
