# ---------- Stage 1: build the React frontend ----------
FROM node:20-slim AS frontend-build
RUN apt-get update && apt-get install -y --no-install-recommends curl ca-certificates && rm -rf /var/lib/apt/lists/*
WORKDIR /app/frontend
COPY frontend/package.json frontend/package-lock.json* ./
RUN npm install
COPY frontend/ ./

# face-api.js's tiny face detector model (used client-side purely for the
# live camera box-drawing UX) is a binary file kept out of git history;
# fetch it at build time instead, straight into the public/ dir Vite copies as-is.
# `-f` makes curl fail the build on a non-2xx response instead of writing an
# error page to disk, and the explicit size check catches the case where
# GitHub serves a "successful" but empty/truncated response (this exact
# combo silently shipped a 0-byte model file once already - the build
# "succeeded" but the kiosk page hung forever on "Loading face tracking...").
# Both files live at the plain raw.githubusercontent.com path, NOT the LFS
# media.githubusercontent.com/media/... path - this file isn't Git-LFS
# tracked in the upstream repo, so that LFS URL 404s.
RUN mkdir -p public/models && \
    curl -sL -f -A "Mozilla/5.0" -o public/models/tiny_face_detector_model-weights_manifest.json \
      "https://raw.githubusercontent.com/vladmandic/face-api/master/model/tiny_face_detector_model-weights_manifest.json" && \
    curl -sL -f -A "Mozilla/5.0" -o public/models/tiny_face_detector_model.bin \
      "https://raw.githubusercontent.com/vladmandic/face-api/master/model/tiny_face_detector_model.bin" && \
    test $(stat -c%s public/models/tiny_face_detector_model-weights_manifest.json) -ge 500 && \
    test $(stat -c%s public/models/tiny_face_detector_model.bin) -ge 100000

RUN npm run build

# ---------- Stage 2: Python backend, serving the built frontend ----------
FROM python:3.11-slim

# opencv-contrib-python-headless still dynamically links against a few
# system image/graphics libs even in "headless" mode.
RUN apt-get update && apt-get install -y --no-install-recommends \
    libglib2.0-0 libsm6 libxext6 libxrender1 libgl1 curl ca-certificates \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

COPY backend/requirements.txt ./requirements.txt
RUN pip install --no-cache-dir -r requirements.txt

COPY backend/ ./

# Face-recognition model is too large to keep in the git history casually;
# fetch it at build time instead (cached as a Docker layer after the first
# build as long as this file doesn't change).
RUN chmod +x download_models.sh && ./download_models.sh

# Bring in the frontend build from stage 1 so FastAPI can serve it directly --
# one service, one deploy, no separate static host or CORS setup needed.
COPY --from=frontend-build /app/frontend/dist ./app/frontend_dist

ENV PYTHONUNBUFFERED=1
EXPOSE 8000

# Railway (and most PaaS providers) inject $PORT at runtime; default to 8000
# for plain `docker run` / local use.
CMD ["sh", "-c", "uvicorn app.main:app --host 0.0.0.0 --port ${PORT:-8000}"]
