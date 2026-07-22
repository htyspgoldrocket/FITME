# FITME 배포 컨테이너 (6-3b) — 단일 유닛: FastAPI가 API + 프론트 dist 정적 서빙(6-3a)
#
# 빌드:  docker build -t fitme .
# 실행:  docker run -p 8000:8000 -e ANTHROPIC_API_KEY=... -e REPLICATE_API_TOKEN=... \
#            -e FITME_BETA_CODE=... fitme
# 호스팅(Railway 등)은 PORT 환경 변수를 주입한다 — 없으면 8000.

# ---------- Stage 1: 프론트 빌드 (dist는 gitignore라 컨테이너 안에서 생성) ----------
FROM node:22-slim AS front
WORKDIR /build
COPY package.json package-lock.json ./
RUN npm ci
COPY index.html tsconfig.json tsconfig.node.json vite.config.ts ./
COPY public ./public
COPY src ./src
RUN npm run build

# ---------- Stage 2: 런타임 (python 3.12 — 로컬 venv 3.12.4와 정합) ----------
FROM python:3.12-slim

ENV PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1

# opencv-python 런타임 공유 라이브러리 (slim 이미지에는 없음: libGL·glib)
RUN apt-get update \
    && apt-get install -y --no-install-recommends libgl1 libglib2.0-0 \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app/server

# 의존성 먼저 복사 — 코드 변경 시 pip/chromium 레이어 캐시 재사용
COPY server/requirements.txt ./
RUN pip install -r requirements.txt
# 무신사 스크래핑용 chromium + OS 의존성 (이미지가 수백 MB 커지는 주범 — 필수라 수용)
RUN playwright install --with-deps chromium

# 백엔드 코드 + 프론트 빌드 산출물 (main.py의 FRONT_DIST = /app/dist)
COPY server/ ./
COPY --from=front /build/dist /app/dist

EXPOSE 8000
CMD ["sh", "-c", "uvicorn main:app --host 0.0.0.0 --port ${PORT:-8000}"]
