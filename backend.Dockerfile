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
        libgdk-pixbuf-2.0-0 \
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

# Install a headless Chromium package so mermaid-cli (which uses Puppeteer)
# can spawn a browser inside the container. This avoids the "Could not find
# Chromium" runtime error from Puppeteer.
RUN apt-get update && \
    apt-get install -y --no-install-recommends chromium && \
    rm -rf /var/lib/apt/lists/* || true

COPY requirements.txt .
RUN pip install --upgrade pip && pip install -r requirements.txt

COPY backend backend
COPY docs ./docs
COPY image.png image.png
# Copy logo files for document generation (same as used in frontend)
COPY frontend/src/assets/logo-transparent.png ./assets/logo-transparent.png
COPY frontend/src/assets/logo.png ./assets/logo.png

EXPOSE 8001

# Install Node.js (18.x) and mermaid-cli (mmdc) so the backend can render Mermaid diagrams locally.
RUN curl -fsSL https://deb.nodesource.com/setup_18.x | bash - && \
    apt-get update && apt-get install -y --no-install-recommends nodejs && \
    npm install -g @mermaid-js/mermaid-cli@10.3.0 && \
    rm -rf /var/lib/apt/lists/* /root/.npm /root/.cache

ENV MERMAID_CLI_PATH=/usr/bin/mmdc
# Point Puppeteer / mermaid-cli at the system Chromium executable when possible
ENV PUPPETEER_EXECUTABLE_PATH=/usr/bin/chromium

CMD ["uvicorn", "backend.app:app", "--host", "0.0.0.0", "--port", "8001"]

