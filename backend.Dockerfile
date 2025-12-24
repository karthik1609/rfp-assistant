FROM python:3.11-slim

ENV PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    PYTHONDONTWRITEBYTECODE=1

WORKDIR /app

RUN apt-get update && \
    apt-get install -y --no-install-recommends \
        poppler-utils \
        libpango-1.0-0 \
        libpangoft2-1.0-0 \
        libfontconfig1 \
        libcairo2 \
        libcairo2-dev \
        libpango1.0-dev \
        libgdk-pixbuf-2.0-0 \
        libgdk-pixbuf-xlib-2.0-dev \
        libffi-dev \
        pkg-config \
        shared-mime-info \
        libgobject-2.0-0 \
        ca-certificates \
        curl \
        gnupg \
        build-essential \
        wget \
        libx11-xcb1 \
        libxcomposite1 \
        libxdamage1 \
        libxrandr2 \
        libgbm1 \
        libasound2 \
        fonts-liberation && \
    rm -rf /var/lib/apt/lists/*

# (Removed) Headless Chromium installation — no longer required; Mermaid
# rendering is performed via an external MCP service (OpenAI Responses API).

COPY requirements.txt .
RUN pip install --upgrade pip && pip install -r requirements.txt

COPY backend backend
COPY docs ./docs
COPY image.png image.png
COPY frontend/src/assets/logo-transparent.png ./assets/logo-transparent.png
COPY frontend/src/assets/logo.png ./assets/logo.png

EXPOSE 8001


CMD ["uvicorn", "backend.app:app", "--host", "0.0.0.0", "--port", "8001"]

