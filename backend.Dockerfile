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
        fonts-liberation \
        # Puppeteer/Chromium dependencies for MCP Mermaid server
        chromium \
        chromium-sandbox \
        libnss3 \
        libatk-bridge2.0-0 \
        libatk1.0-0 \
        libcups2 \
        libdrm2 \
        libdbus-1-3 \
        libxkbcommon0 \
        libxcomposite1 \
        libxdamage1 \
        libxfixes3 \
        libxrandr2 \
        libgbm1 \
        libasound2 \
        libpangocairo-1.0-0 \
        libcairo-gobject2 \
        libgtk-3-0 && \
    rm -rf /var/lib/apt/lists/*

# Install Node.js and npm for MCP Mermaid server
RUN curl -fsSL https://deb.nodesource.com/setup_20.x | bash - && \
    apt-get install -y --no-install-recommends nodejs && \
    rm -rf /var/lib/apt/lists/*

# Set Puppeteer/Playwright to use system Chromium
ENV PUPPETEER_SKIP_CHROMIUM_DOWNLOAD=true \
    PUPPETEER_EXECUTABLE_PATH=/usr/bin/chromium \
    PLAYWRIGHT_BROWSERS_PATH=/usr/bin \
    PLAYWRIGHT_SKIP_BROWSER_DOWNLOAD=1

COPY requirements.txt .
RUN pip install --upgrade pip && \
    pip install -r requirements.txt

COPY backend backend
COPY docs ./docs
COPY image.png image.png
COPY frontend/src/assets/logo-transparent.png ./assets/logo-transparent.png
COPY frontend/src/assets/logo.png ./assets/logo.png

EXPOSE 8001


CMD ["uvicorn", "backend.app:app", "--host", "0.0.0.0", "--port", "8001"]

