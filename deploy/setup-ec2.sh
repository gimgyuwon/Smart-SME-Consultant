#!/bin/bash
# ──────────────────────────────────────────────────────────────
# deploy/setup-ec2.sh — AWS EC2 초기 설정 스크립트
# Ubuntu 22.04 LTS 기준
# 사용법: chmod +x setup-ec2.sh && sudo ./setup-ec2.sh
# ──────────────────────────────────────────────────────────────
set -e  # 에러 발생 시 즉시 종료

echo "================================================================"
echo " 🛡️  소상공인 흑자도산 방지 대시보드 — EC2 환경 설정"
echo "================================================================"

# ── 1. 시스템 업데이트 ─────────────────────────────────────────
echo ""
echo "[1/5] 시스템 패키지 업데이트..."
apt-get update -y
apt-get upgrade -y

# ── 2. Docker 설치 ─────────────────────────────────────────────
echo ""
echo "[2/5] Docker 설치..."
if command -v docker &>/dev/null; then
    echo "  ✓ Docker 이미 설치됨: $(docker --version)"
else
    curl -fsSL https://get.docker.com | bash
    usermod -aG docker ubuntu   # ubuntu 유저에게 docker 권한 부여
    echo "  ✓ Docker 설치 완료"
fi

# ── 3. Docker Compose v2 설치 ──────────────────────────────────
echo ""
echo "[3/5] Docker Compose 설치..."
if command -v docker compose &>/dev/null 2>&1; then
    echo "  ✓ Docker Compose 이미 설치됨"
else
    COMPOSE_VERSION=$(curl -s https://api.github.com/repos/docker/compose/releases/latest \
        | grep '"tag_name"' | cut -d'"' -f4)
    curl -SL "https://github.com/docker/compose/releases/download/${COMPOSE_VERSION}/docker-compose-linux-x86_64" \
        -o /usr/local/bin/docker-compose
    chmod +x /usr/local/bin/docker-compose
    ln -sf /usr/local/bin/docker-compose /usr/bin/docker-compose
    echo "  ✓ Docker Compose ${COMPOSE_VERSION} 설치 완료"
fi

# ── 4. 유용한 도구 설치 ────────────────────────────────────────
echo ""
echo "[4/5] 유틸리티 설치..."
apt-get install -y --no-install-recommends \
    git \
    curl \
    htop \
    ufw

# ── 5. 방화벽 설정 ─────────────────────────────────────────────
echo ""
echo "[5/5] UFW 방화벽 설정..."
ufw allow 22/tcp    # SSH
ufw allow 80/tcp    # HTTP
ufw allow 443/tcp   # HTTPS
ufw --force enable
echo "  ✓ 방화벽 설정 완료 (22, 80, 443 허용)"

echo ""
echo "================================================================"
echo " ✅ EC2 초기 설정 완료!"
echo "================================================================"
echo ""
echo " 다음 단계:"
echo "   1. 로그아웃 후 재접속 (docker 그룹 권한 적용)"
echo "   2. git clone https://github.com/<user>/data_anal.git"
echo "   3. cd data_anal"
echo "   4. docker compose -f docker-compose.prod.yml up -d --build"
echo ""
