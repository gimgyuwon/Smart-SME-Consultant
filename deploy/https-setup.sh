#!/bin/bash
# ──────────────────────────────────────────────────────────────
# deploy/https-setup.sh — Let's Encrypt HTTPS 설정 스크립트
# 도메인이 EC2 IP에 연결된 후 실행
# 사용법: sudo ./https-setup.sh your-domain.com your@email.com
# ──────────────────────────────────────────────────────────────
set -e

DOMAIN="${1:-}"
EMAIL="${2:-}"

if [ -z "$DOMAIN" ] || [ -z "$EMAIL" ]; then
    echo "❌ 사용법: $0 <도메인> <이메일>"
    echo "   예시:  $0 example.com admin@example.com"
    exit 1
fi

echo "================================================================"
echo " 🔐 HTTPS 설정 시작: $DOMAIN"
echo "================================================================"

# ── 1. 인증서 디렉토리 생성 ────────────────────────────────────
mkdir -p deploy/certbot/conf deploy/certbot/www

# ── 2. Nginx를 HTTP 전용으로 먼저 올리기 (인증 필요) ───────────
echo "[1/3] HTTP 전용 Nginx 시작 (인증서 발급용)..."
docker compose -f docker-compose.prod.yml up -d nginx

# ── 3. Let's Encrypt 인증서 발급 ───────────────────────────────
echo "[2/3] Let's Encrypt 인증서 발급..."
docker compose -f docker-compose.prod.yml run --rm certbot \
    certonly \
    --webroot \
    --webroot-path=/var/www/certbot \
    --email "$EMAIL" \
    --agree-tos \
    --no-eff-email \
    -d "$DOMAIN"

echo "  ✓ 인증서 발급 완료"

# ── 4. nginx.conf에 도메인 적용 ────────────────────────────────
echo "[3/3] Nginx HTTPS 설정 적용..."
# 주석 처리된 HTTPS 블록 활성화, 도메인 치환
sed -i "s|your-domain.com|$DOMAIN|g" deploy/nginx.conf
sed -i '/# ── HTTPS/,/# ── IP/{s/^# //}' deploy/nginx.conf      # HTTPS 블록 주석 해제
sed -i '/── IP 직접 접속/,/^}/s/^/# /' deploy/nginx.conf        # IP 직접 접속 블록 주석 처리

# Nginx 재시작
docker compose -f docker-compose.prod.yml restart nginx

echo ""
echo "================================================================"
echo " ✅ HTTPS 설정 완료!"
echo "================================================================"
echo ""
echo " 🌍 접속 URL: https://$DOMAIN"
echo " 🔄 인증서 자동 갱신: 12시간마다 체크 (certbot 컨테이너)"
echo ""
