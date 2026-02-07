# ============================================================================
# Ignition Toolbox - Docker Build
# Multi-stage: build frontend, then assemble runtime with Python + Playwright
# ============================================================================

# Stage 1: Build React frontend
FROM node:22-slim AS frontend-builder

WORKDIR /build/frontend
COPY frontend/package.json frontend/package-lock.json* ./
RUN npm ci --ignore-scripts

COPY frontend/ ./
RUN npm run build


# Stage 2: Runtime - Python backend + built frontend + Playwright
FROM python:3.13-slim AS runtime

# Prevent Python from writing .pyc files and enable unbuffered output
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

WORKDIR /app

# Install system dependencies for Playwright and Docker CLI
RUN apt-get update && apt-get install -y --no-install-recommends \
    # Playwright Chromium dependencies
    libnss3 \
    libnspr4 \
    libatk1.0-0 \
    libatk-bridge2.0-0 \
    libcups2 \
    libdrm2 \
    libdbus-1-3 \
    libxkbcommon0 \
    libatspi2.0-0 \
    libxcomposite1 \
    libxdamage1 \
    libxfixes3 \
    libxrandr2 \
    libgbm1 \
    libpango-1.0-0 \
    libcairo2 \
    libasound2 \
    libwayland-client0 \
    # Font support
    fonts-liberation \
    fonts-noto-color-emoji \
    # Docker CLI (for CloudDesigner)
    ca-certificates \
    curl \
    gnupg \
    && install -m 0755 -d /etc/apt/keyrings \
    && curl -fsSL https://download.docker.com/linux/debian/gpg | gpg --dearmor -o /etc/apt/keyrings/docker.gpg \
    && chmod a+r /etc/apt/keyrings/docker.gpg \
    && echo "deb [arch=$(dpkg --print-architecture) signed-by=/etc/apt/keyrings/docker.gpg] https://download.docker.com/linux/debian $(. /etc/os-release && echo "$VERSION_CODENAME") stable" > /etc/apt/sources.list.d/docker.list \
    && apt-get update \
    && apt-get install -y --no-install-recommends docker-ce-cli docker-compose-plugin \
    && apt-get clean \
    && rm -rf /var/lib/apt/lists/*

# Install Python dependencies
COPY backend/requirements.txt /app/backend/requirements.txt
RUN pip install --no-cache-dir -r /app/backend/requirements.txt \
    && pip uninstall -y pyinstaller \
    && rm -rf /root/.cache/pip

# Install Playwright Chromium browser
RUN playwright install chromium

# Create non-root user for runtime security
RUN groupadd --gid 1000 toolbox \
    && useradd --uid 1000 --gid toolbox --shell /bin/bash --create-home toolbox

# Copy backend source
COPY backend/ /app/backend/

# Copy built frontend into the path expected by app.py:
# Path(__file__).parent.parent.parent / "frontend" / "dist"
# From backend/ignition_toolkit/api/app.py -> backend/frontend/dist
COPY --from=frontend-builder /build/frontend/dist /app/backend/frontend/dist

# Create data directory for SQLite, credentials, screenshots
# and set ownership to non-root user
RUN mkdir -p /data && chown -R toolbox:toolbox /data /app

# Environment configuration
ENV IGNITION_TOOLKIT_HOST=0.0.0.0 \
    IGNITION_TOOLKIT_PORT=5000 \
    IGNITION_TOOLKIT_DATA=/data

EXPOSE 5000

# Health check using the existing /health endpoint
HEALTHCHECK --interval=30s --timeout=10s --start-period=15s --retries=3 \
    CMD python -c "import urllib.request; urllib.request.urlopen('http://localhost:5000/health')" || exit 1

WORKDIR /app/backend

# Run as non-root user
# Note: Docker socket access requires the toolbox user to be in the docker group
# or the socket to have appropriate permissions. When using docker-compose.yml,
# ensure the docker socket is readable: "- /var/run/docker.sock:/var/run/docker.sock:ro"
USER toolbox

CMD ["python", "run_backend.py"]
