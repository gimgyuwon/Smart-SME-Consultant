# Build Stage
FROM python:3.11-slim-bookworm AS builder

WORKDIR /install

# apt 미러를 안정 소스로 고정 후 패키지 설치
RUN apt-get update --fix-missing && apt-get install -y --no-install-recommends \
        default-jre-headless \
        gcc \
        g++ \
        curl \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install --no-cache-dir --prefix=/install/deps -r requirements.txt


# Runtime Stage
FROM python:3.11-slim-bookworm AS runtime

RUN apt-get update --fix-missing && apt-get install -y --no-install-recommends \
        default-jre-headless \
        curl \
    && rm -rf /var/lib/apt/lists/*

# JAVA_HOME (Bookworm 기준 경로)
ENV JAVA_HOME=/usr/lib/jvm/java-17-openjdk-amd64
ENV PATH="${JAVA_HOME}/bin:${PATH}"
ENV PYTHONPATH=/app

# 비 root 사용자
RUN useradd -m -u 1000 appuser

WORKDIR /app

# 빌드 스테이지 패키지 복사
COPY --from=builder /install/deps /usr/local

# 소스 복사
COPY --chown=appuser:appuser . .

USER appuser

EXPOSE 8501

HEALTHCHECK --interval=30s --timeout=10s --start-period=90s --retries=3 \
    CMD curl -f http://localhost:8501/_stcore/health || exit 1

ENTRYPOINT ["streamlit", "run", "app.py", \
    "--server.port=8501", \
    "--server.address=0.0.0.0", \
    "--server.headless=true", \
    "--server.enableCORS=false", \
    "--server.enableXsrfProtection=false", \
    "--browser.gatherUsageStats=false"]
