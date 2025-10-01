# syntax=docker/dockerfile:1

############################
# 1. Build stage
############################
FROM python:3.11-slim AS builder

WORKDIR /app

# 시스템 패키지 (빌드에만 필요)
RUN apt-get update \
    && apt-get install -y --no-install-recommends \
       build-essential gcc \
    && rm -rf /var/lib/apt/lists/*

# pip 최신화 + 패키지 설치 (빌드 환경)
COPY requirements.txt .
RUN pip install --upgrade pip \
    && pip install --prefix=/install -r requirements.txt


############################
# 2. Runtime stage
############################
FROM python:3.11-slim AS runtime

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    PYTHONPATH=/app/src

WORKDIR /app

# builder에서 설치한 패키지만 복사
COPY --from=builder /install /usr/local

# 프로젝트 소스 복사
COPY . .

EXPOSE 8000

CMD ["uvicorn", "app.server:app", "--host", "0.0.0.0", "--port", "8000"]